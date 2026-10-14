"""Packaging boundaries; fixture MP4s test the parser, not real playback."""

from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_midterm as packaging


def box(kind, payload):
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


def mp4_fixture(seconds=30, video=True, version=0):
    if version == 0:
        header = bytes(12) + struct.pack(">II", 1000, int(seconds * 1000)) + bytes(80)
    else:
        header = bytes([1]) + bytes(19) + struct.pack(">IQ", 1000, int(seconds * 1000)) + bytes(80)
    handler = bytes(8) + (b"vide" if video else b"soun") + bytes(12)
    track = box(b"trak", box(b"mdia", box(b"hdlr", handler)))
    return box(b"ftyp", b"isom" + bytes(4) + b"mp42") + box(b"moov", box(b"mvhd", header) + track) + box(b"mdat", b"test media")


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.video = self.root / "recording.mp4"
        self.video.write_bytes(mp4_fixture())
        self.status = self.root / "status.pdf"
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with self.status.open("wb") as handle:
            writer.write(handle)

    def tearDown(self):
        self.temporary.cleanup()

    def package(self, **overrides):
        options = {"video": self.video, "repository_url": "https://github.com/course-team/ailt9019", "status_sheet": self.status, "output": self.root / "submission.zip", "confirm_official_template": True, "confirm_contributions": True}
        options.update(overrides)
        # Synthetic fixture validates deterministic container parsing only.
        with patch.object(packaging.shutil, "which", return_value=None):
            return packaging.package_submission(**options)

    def test_exact_three_entries_and_url(self):
        result = self.package()
        self.assertEqual(result["video_seconds"], 30)
        with zipfile.ZipFile(result["output"]) as archive:
            self.assertEqual(archive.namelist(), ["video.mp4", "repository_link.txt", "status_sheet.pdf"])
            self.assertEqual(archive.read("repository_link.txt"), b"https://github.com/course-team/ailt9019\n")
            self.assertIsNone(archive.testzip())

    def test_rejects_missing_human_attestations(self):
        for option in ("confirm_official_template", "confirm_contributions"):
            with self.subTest(option=option), self.assertRaises(packaging.SubmissionError):
                self.package(**{option: False})
        self.assertFalse((self.root / "submission.zip").exists())

    def test_repository_url_rejects_placeholders_and_non_repository_urls(self):
        urls = ["https://github.com/OWNER/REPOSITORY", "https://github.com/example/ailt9019", "https://github.com/ACTUAL-TEAM/ACTUAL-PROJECT", "https://github.com/team/.git", "https://github.com/team/..", "http://github.com/team/ailt9019", "https://github.com/team/ailt9019/tree/main", "https://github.com/team/ailt9019?tab=readme", "https://github.com.evil.test/team/ailt9019", "https://user@github.com/team/ailt9019"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(packaging.SubmissionError):
                packaging.validate_repository_url(url)

    def test_rejects_overlong_and_zero_video(self):
        for seconds in (60.001, 0):
            self.video.write_bytes(mp4_fixture(seconds))
            with self.subTest(seconds=seconds), self.assertRaises(packaging.SubmissionError):
                self.package()

    def test_allows_exact_sixty_seconds_and_version_one(self):
        self.video.write_bytes(mp4_fixture(60, version=1))
        self.assertEqual(self.package()["video_seconds"], 60)

    def test_rejects_truncated_fake_or_audio_only_recording(self):
        for data in (b"not a recording", mp4_fixture()[:-2], mp4_fixture(video=False), box(b"moov", b"")):
            self.video.write_bytes(data)
            with self.subTest(data_length=len(data)), self.assertRaises(packaging.SubmissionError):
                self.package()

    def test_rejects_missing_file(self):
        with self.assertRaises(packaging.SubmissionError):
            self.package(video=self.root / "missing.mp4")

    def test_rejects_multiple_page_or_corrupt_pdf(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        for _ in range(2):
            writer.add_blank_page(width=595, height=842)
        with self.status.open("wb") as handle:
            writer.write(handle)
        with self.assertRaises(packaging.SubmissionError):
            self.package()
        self.status.write_bytes(b"not a PDF")
        with self.assertRaises(packaging.SubmissionError):
            self.package()

    def test_rejects_oversize_and_removes_temporary_zip(self):
        with patch.object(packaging, "MAX_ZIP_BYTES", 1), self.assertRaises(packaging.SubmissionError):
            self.package()
        self.assertEqual(list(self.root.glob("*.zip")), [])

    def test_existing_output_is_not_overwritten(self):
        output = self.root / "submission.zip"
        output.write_bytes(b"existing work")
        with self.assertRaises(packaging.SubmissionError):
            self.package()
        self.assertEqual(output.read_bytes(), b"existing work")

    def test_ffprobe_failure_does_not_silently_fall_back(self):
        import subprocess
        with patch.object(packaging.shutil, "which", return_value="ffprobe"), patch.object(packaging.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "ffprobe")), self.assertRaises(packaging.SubmissionError):
            packaging.validate_video(self.video)


if __name__ == "__main__":
    unittest.main()
