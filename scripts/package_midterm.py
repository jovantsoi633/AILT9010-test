"""Validate genuine submission inputs and create the three-file midterm ZIP.

This command does not turn drafts, simulated answers, or unverified contributions
into submission evidence. Its confirmation flags are explicit human attestations.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from urllib.parse import urlsplit
import zipfile


MAX_VIDEO_SECONDS = 60.0
MAX_ZIP_BYTES = 100_000_000


class SubmissionError(ValueError):
    """A submission input is missing, invalid, or not confirmed."""


def validate_repository_url(value: str) -> str:
    """Accept an HTTPS GitHub repository URL, not a placeholder or a subpage."""
    value = value.strip()
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.query
        or parsed.fragment
    ):
        raise SubmissionError("Use a real https://github.com/OWNER/REPOSITORY URL.")
    parts = parsed.path.strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise SubmissionError("Repository URL must identify one owner and one repository.")
    owner, repository = parts
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner):
        raise SubmissionError("Invalid GitHub repository owner.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", repository):
        raise SubmissionError("Invalid GitHub repository name.")
    placeholders = {"owner", "username", "your-name", "your-username", "your-org", "example", "placeholder", "todo", "tbd", "repo", "repository", "your-repo", "your-repository"}
    if owner.lower() in placeholders or repository.lower() in placeholders or owner.lower().startswith("actual-") or repository.lower().startswith("actual-"):
        raise SubmissionError("Replace placeholder repository information before packaging.")
    repository = repository.removesuffix(".git")
    if repository in {"", ".", ".."}:
        raise SubmissionError("Invalid GitHub repository name.")
    return f"https://github.com/{owner}/{repository}"


def _require_file(path: Path, suffix: str) -> Path:
    path = path.resolve()
    if not path.is_file():
        raise SubmissionError(f"Input file does not exist: {path}")
    if path.suffix.lower() != suffix:
        raise SubmissionError(f"Expected a {suffix} file: {path.name}")
    if path.stat().st_size == 0:
        raise SubmissionError(f"Input file is empty: {path.name}")
    return path


def _boxes(handle, start: int, end: int):
    """Walk bounded ISO base media boxes without loading video payloads."""
    position = start
    while position < end:
        if end - position < 8:
            raise SubmissionError("Invalid MP4: truncated box header.")
        handle.seek(position)
        size, kind = struct.unpack(">I4s", handle.read(8))
        header_size = 8
        if size == 1:
            if end - position < 16:
                raise SubmissionError("Invalid MP4: truncated extended box header.")
            size = struct.unpack(">Q", handle.read(8))[0]
            header_size = 16
        elif size == 0:
            size = end - position
        if size < header_size or position + size > end:
            raise SubmissionError("Invalid MP4: box exceeds file or parent bounds.")
        yield kind, position + header_size, position + size
        position += size


def _movie_duration(handle, start: int, end: int) -> float:
    handle.seek(start)
    header = handle.read(min(32, end - start))
    if not header:
        raise SubmissionError("Invalid MP4: empty movie header.")
    version = header[0]
    if version == 0 and len(header) >= 20:
        timescale, duration = struct.unpack(">II", header[12:20])
        unknown_duration = 0xFFFFFFFF
    elif version == 1 and len(header) >= 32:
        timescale, duration = struct.unpack(">IQ", header[20:32])
        unknown_duration = 0xFFFFFFFFFFFFFFFF
    else:
        raise SubmissionError("Invalid MP4: unsupported or truncated movie header.")
    if timescale == 0 or duration == unknown_duration:
        raise SubmissionError("MP4 duration is unavailable; export a complete recording.")
    return duration / timescale


def _is_video_track(handle, start: int, end: int) -> bool:
    for kind, payload_start, box_end in _boxes(handle, start, end):
        if kind != b"mdia":
            continue
        for child_kind, child_start, child_end in _boxes(handle, payload_start, box_end):
            if child_kind == b"hdlr" and child_end - child_start >= 12:
                handle.seek(child_start + 8)
                if handle.read(4) == b"vide":
                    return True
    return False


def _header_video_duration(path: Path) -> float:
    """Fallback when ffprobe is absent: inspect MP4 structure and movie duration."""
    durations = []
    has_ftyp = False
    has_video = False
    has_media = False
    with path.open("rb") as handle:
        for kind, start, end in _boxes(handle, 0, path.stat().st_size):
            if kind == b"ftyp":
                if end - start < 8 or end - start > 4096:
                    raise SubmissionError("Invalid MP4: truncated file type box.")
                handle.seek(start)
                brands = handle.read(end - start)
                known = {b"isom", b"iso2", b"mp41", b"mp42", b"avc1", b"M4V ", b"MSNV", b"dash"}
                has_ftyp = any(brands[i : i + 4] in known or brands[i : i + 3] == b"iso" for i in [0, *range(8, len(brands), 4)])
            elif kind == b"mdat":
                has_media = has_media or end > start
            elif kind == b"moov":
                for child_kind, child_start, child_end in _boxes(handle, start, end):
                    if child_kind == b"mvhd":
                        durations.append(_movie_duration(handle, child_start, child_end))
                    elif child_kind == b"trak":
                        has_video = has_video or _is_video_track(handle, child_start, child_end)
    if not (has_ftyp and has_media and has_video and len(durations) == 1):
        raise SubmissionError("MP4 must contain a complete movie header, video track, and media data.")
    return durations[0]


def validate_video(path: Path) -> tuple[Path, float]:
    path = _require_file(path, ".mp4")
    duration = _header_video_duration(path)
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,duration", "-of", "json", str(path)],
                check=True, capture_output=True, text=True, timeout=30,
            )
            info = json.loads(result.stdout)
            streams = info.get("streams", [])
            if not any(stream.get("codec_type") == "video" for stream in streams):
                raise SubmissionError("Recording does not contain a video stream.")
            available = [duration]
            for item in [info.get("format", {}), *streams]:
                if item.get("duration") not in (None, "N/A"):
                    available.append(float(item["duration"]))
            duration = max(available)
        except (subprocess.SubprocessError, ValueError, TypeError) as exc:
            raise SubmissionError("ffprobe could not validate the MP4 recording.") from exc
    if not math.isfinite(duration) or duration <= 0 or duration > MAX_VIDEO_SECONDS:
        raise SubmissionError(f"Recording must be longer than 0 and at most 60 seconds; detected {duration:.3f}s.")
    return path, duration


def validate_status_sheet(path: Path) -> Path:
    path = _require_file(path, ".pdf")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SubmissionError("Install project requirements first: pypdf is needed to verify the PDF page count.") from exc
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted or len(reader.pages) != 1:
            raise SubmissionError("Status sheet must be an unencrypted one-page PDF.")
    except SubmissionError:
        raise
    except Exception as exc:
        raise SubmissionError("Cannot read the status sheet as a valid PDF.") from exc
    return path


def package_submission(
    video: Path,
    repository_url: str,
    status_sheet: Path,
    output: Path,
    *,
    confirm_official_template: bool = False,
    confirm_contributions: bool = False,
) -> dict:
    if not confirm_official_template:
        raise SubmissionError("Confirm that the final status sheet uses the Moodle companion template.")
    if not confirm_contributions:
        raise SubmissionError("Confirm that all names, contributions, and reported results are verified and contain no placeholders.")
    repository_url = validate_repository_url(repository_url)
    video, duration = validate_video(Path(video))
    status_sheet = validate_status_sheet(Path(status_sheet))
    output = Path(output).resolve()
    if output.suffix.lower() != ".zip":
        raise SubmissionError("Output filename must end in .zip.")
    if output.exists():
        raise SubmissionError(f"Output already exists; choose a new filename: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".midterm-", suffix=".zip", dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(video, "video.mp4")
            archive.writestr("repository_link.txt", repository_url + "\n")
            archive.write(status_sheet, "status_sheet.pdf")
        size = temporary.stat().st_size
        if size > MAX_ZIP_BYTES:
            raise SubmissionError(f"ZIP is {size:,} bytes; limit is {MAX_ZIP_BYTES:,} bytes.")
        with zipfile.ZipFile(temporary) as archive:
            if archive.namelist() != ["video.mp4", "repository_link.txt", "status_sheet.pdf"] or archive.testzip() is not None:
                raise SubmissionError("Generated ZIP failed its integrity check.")
        # Use an exclusive create so an existing file cannot be overwritten even
        # if another process creates it between the initial check and this point.
        created_output = False
        try:
            with output.open("xb") as destination, temporary.open("rb") as source:
                created_output = True
                shutil.copyfileobj(source, destination)
        except Exception:
            if created_output:
                output.unlink(missing_ok=True)
            raise
        return {"output": str(output), "size_bytes": size, "video_seconds": round(duration, 3), "repository_url": repository_url}
    except FileExistsError as exc:
        raise SubmissionError("Output appeared during packaging; choose a new filename.") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--status-sheet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-official-template", action="store_true", help="Attest that the PDF follows the actual Moodle companion template.")
    parser.add_argument("--confirm-contributions", action="store_true", help="Attest that names, contributions, results, and evidence are verified; no placeholders remain.")
    args = parser.parse_args(argv)
    try:
        result = package_submission(args.video, args.repository_url, args.status_sheet, args.output, confirm_official_template=args.confirm_official_template, confirm_contributions=args.confirm_contributions)
    except SubmissionError as exc:
        parser.exit(2, f"Submission not packaged: {exc}\n")
    print(json.dumps(result, indent=2))
    print("Packaged validated files. Separately verify course-team repository access, video readability, and Moodle receipt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
