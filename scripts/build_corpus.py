"""Rebuild the checked-in prose corpus from the pinned OpenStax PDF.

No model, OCR, paraphrasing, downloading, or API credentials are involved.
Uses the pdfplumber version pinned in requirements.txt and records its installed
version in the source manifest. Run from any working directory.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://d3bxy9euw4e147.cloudfront.net/oscms-prodcms/media/documents/Economics2e-LR.pdf"
BOOK_URL = "https://openstax.org/details/books/principles-economics-2e"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
SOURCE_SHA256 = "4294836051532268aa0ffd3f2926db9b1b9e620fad415f73d3941265d063feca"
DOWNLOAD_LINE = f"Download for free at {BOOK_URL}."
ATTRIBUTION = (
    "Principles of Economics 2e, OpenStax; senior contributing authors Steven A. Greenlaw "
    "and David Shapiro. ©2018 Rice University. "
    f"Licensed under CC BY 4.0 ({LICENSE_URL}). {DOWNLOAD_LINE} "
    "Excerpt: PDF line wrapping and whitespace normalized; diagrams, equations, tables, "
    "and navigation omitted. Portions of Demand and Supply derive from Steve Greenlaw "
    "and Lumen Learning, Why It Matters: Government in Action, CC BY 4.0 "
    "(https://courses.lumenlearning.com/waymakermacroxmasterfall2016/chapter/why-it-matters-government-action/)."
)
SECTIONS = {
    "3.1": "Demand, Supply, and Equilibrium in Markets for Goods and Services",
    "3.2": "Shifts in Demand and Supply for Goods and Services",
    "3.3": "Changes in Equilibrium Price and Quantity: The Four-Step Process",
    "3.4": "Price Ceilings and Price Floors",
    "3.5": "Demand, Supply, and Efficiency",
    "5.1": "Price Elasticity of Demand and Price Elasticity of Supply",
    "5.2": "Polar Cases of Elasticity and Constant Elasticity",
    "5.3": "Elasticity and Pricing",
    "5.4": "Elasticity in Areas Other Than Price",
}
CHAPTERS = {"3": "Demand and Supply", "5": "Elasticity"}
RANGES = ((56, 84), (118, 136))  # one-based PDF pages; body sections only


def normalize_lines(lines: list[str]) -> str:
    """Join visual lines without changing words; preserve printed line-end hyphens."""
    result = ""
    for line in lines:
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        separator = "" if result.endswith("-") else " "
        result += (separator if result else "") + line
    return result.strip()


def validate_source(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"Missing source PDF: {path}. Download the pinned URL documented in docs/data_notes.md.")
    with path.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != SOURCE_SHA256:
        raise ValueError(f"Source checksum mismatch: {actual}; expected {SOURCE_SHA256}. Refusing to rebuild.")


def line_kind(line: dict[str, Any]) -> str | None:
    chars = line["chars"]
    if line["top"] < 45 or line["bottom"] > 745:
        return None
    # Text in the main serif body or the indented explanatory feature boxes.
    if any("LiberationSerif" in c["fontname"] and 9.4 <= c["size"] <= 10.1 for c in chars):
        return "body"
    if abs(line["x0"] - 89.1) < 1.1 and any(8.8 <= c["size"] <= 9.1 for c in chars) and all(
        6.5 <= c["size"] <= 9.1 and "LiberationSans" in c["fontname"] for c in chars
    ):
        return "feature"
    return None


def extract_passages(path: Path) -> list[dict[str, Any]]:
    """Use actual line geometry to retain original paragraphs, including page continuations."""
    import pdfplumber

    validate_source(path)
    paragraphs: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    section: str | None = None
    objectives = False
    previous_line: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal active
        if active:
            text = normalize_lines(active.pop("lines"))
            # Link panels and equation-bearing paragraphs are deliberately omitted.
            complete = text.endswith((".", "!", "?", ".”", '."', ".)", "?)")) and not text[0].islower()
            if complete and not active.pop("has_equation") and len(text.split()) >= 16 and not re.search(
                r"(?:Visit this website|Read this article|enjoy this article|http://openstaxcollege\.org)", text,
                flags=re.IGNORECASE,
            ):
                active["text"] = text
                paragraphs.append(active)
        active = None

    with pdfplumber.open(path) as pdf:
        copyright_text = normalize_lines(pdf.pages[3].extract_text(x_tolerance=1).splitlines())
        required = ["©2018 Rice University", "Attribution 4.0 International License", "PE2-2017-002-(03/18)-LC"]
        if not all(token in copyright_text for token in required):
            raise ValueError("Pinned source copyright/edition verification failed.")
        for first, last in RANGES:
            flush()
            section = None
            previous_line = None
            for page_number in range(first, last + 1):
                page = pdf.pages[page_number - 1]
                caption_bottom: float | None = None
                for line in page.extract_text_lines(x_tolerance=1, y_tolerance=5):
                    text = line["text"]
                    if re.match(r"Figure\s+[35]\.\d+\b", text) and not any(
                        "LiberationSerif" in c["fontname"] for c in line["chars"]
                    ):
                        flush()
                        caption_bottom = line["bottom"]
                        previous_line = None
                        continue
                    if caption_bottom is not None:
                        if line["top"] - caption_bottom < 5:
                            caption_bottom = line["bottom"]
                            continue
                        caption_bottom = None
                    heading = re.match(r"([35]\.[1-5])\s*\|", text)
                    if heading:
                        flush()
                        section = heading.group(1)
                        objectives = True
                        previous_line = None
                        continue
                    if section is None or line["top"] < 45 or line["bottom"] > 745:
                        continue
                    if text.startswith("By the end of this section"):
                        continue
                    if objectives:
                        if text.startswith("•") or line["x0"] > 85 or max(c["size"] for c in line["chars"]) > 15:
                            continue
                        objectives = False
                    kind = line_kind(line)
                    if kind is None:
                        # Larger headings, graphics, captions, and tables delimit paragraphs.
                        if active:
                            flush()
                        previous_line = None
                        continue
                    same_page = active and active["pdf_page_end"] == page_number
                    gap = line["top"] - previous_line["bottom"] if same_page and previous_line else 0
                    previous_ends = active and normalize_lines(active["lines"]).endswith((".", "!", "?", ".”", '."', ".)"))
                    continuation = (
                        active and not same_page and active["section"] == section
                        and active["kind"] == kind and not previous_ends
                    )
                    if active and not continuation and (
                        not same_page or gap >= 5 or active["kind"] != kind
                    ):
                        flush()
                    if active is None:
                        active = {
                            "section": section, "pdf_page": page_number, "pdf_page_end": page_number,
                            "kind": kind, "lines": [], "has_equation": False, "source_spans": [],
                        }
                    active["lines"].append(text)
                    active["pdf_page_end"] = page_number
                    active["has_equation"] |= any("STIX" in c["fontname"] for c in line["chars"])
                    active["source_spans"].append({
                        "pdf_page": page_number, "top": round(line["top"], 3),
                        "bottom": round(line["bottom"], 3), "text": text,
                    })
                    previous_line = line
            flush()

    counts: Counter[tuple[str, int]] = Counter()
    result = []
    for item in paragraphs:
        section = item["section"]
        page_number = item["pdf_page"]
        counts[(section, page_number)] += 1
        ordinal = counts[(section, page_number)]
        chapter = section.split(".")[0]
        spans = item.pop("source_spans")
        text = item["text"]
        result.append({
            "id": f"ch{chapter}-s{section.replace('.', '-')}-p{page_number:03d}-{ordinal:02d}",
            "text": text, "chapter": chapter, "chapter_title": CHAPTERS[chapter],
            "section": section, "section_title": SECTIONS[section],
            "pdf_page": page_number, "pdf_page_end": item["pdf_page_end"],
            "printed_page": page_number - 10, "printed_page_end": item["pdf_page_end"] - 10,
            "source": SOURCE_URL, "attribution": ATTRIBUTION,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "source_spans": spans,
        })
    return result


def build_manifest(passages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "title": "Principles of Economics 2e",
        "edition": "2e; pinned March 2018 revision PE2-2017-002-(03/18)-LC",
        "authors": ["Steven A. Greenlaw", "David Shapiro"],
        "authors_role": "senior contributing authors",
        "publisher": "OpenStax, Rice University",
        "copyright": "©2018 Rice University",
        "original_publication_year": 2017,
        "source_url": SOURCE_URL,
        "book_url": BOOK_URL,
        "book_url_note": "The original 2e details URL now redirects to 3e; the pinned PDF checksum identifies the actual 2e source.",
        "source_sha256": SOURCE_SHA256,
        "source_pdf_pages": 974,
        "source_pdf_isbn13": "978-1-947172-37-1",
        "downloaded_on": "2026-10-15",
        "verified_on": "2026-10-15",
        "copyright_page": {"pdf_page": 4, "printed_page": None},
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "license_url": LICENSE_URL,
        "required_download_attribution": DOWNLOAD_LINE,
        "attribution": ATTRIBUTION,
        "scope": [
            {"chapter": "3", "title": CHAPTERS["3"], "sections": ["3.1", "3.2", "3.3", "3.4", "3.5"], "pdf_pages": [56, 84], "printed_pages": [46, 74]},
            {"chapter": "5", "title": CHAPTERS["5"], "sections": ["5.1", "5.2", "5.3", "5.4"], "pdf_pages": [118, 136], "printed_pages": [108, 126]},
        ],
        "passage_count": len(passages),
        "passages_by_section": dict(sorted(Counter(p["section"] for p in passages).items())),
        "extraction": {
            "tool": "pdfplumber", "version": version("pdfplumber"), "x_tolerance": 1, "y_tolerance": 5,
            "paragraph_boundary": "visual line gap >=5 points; font/layout category changes; section/headings",
            "cross_page": "unfinished paragraphs are joined only across adjacent pages in the same section and text category",
            "minimum_words": 16,
            "stable_id": "chapter + section + one-based starting PDF page + paragraph ordinal",
            "modifications": ["Normalized whitespace and visual line wrapping; no paraphrasing or AI rewriting.", "Retained printed line-end hyphens while joining their next line without inserting a space.", "Rendered subscript/superscript labels as ordinary text (e.g. D0).", "Omitted non-prose layout blocks, equation-bearing paragraphs, navigation and short fragments."],
        },
        "exclusions": ["chapter opening introductions before 3.1/5.1", "learning objectives", "end-of-chapter key terms, summaries, review questions and exercises", "diagrams and their captions", "tables", "display equations and prose paragraphs with embedded equation glyphs", "external-link panels", "repeated page headers/footers", "cover, logos and other trademark images"],
        "limitations": ["This is a prose excerpt corpus, not a complete digital reproduction of the chapters.", "Questions that require diagrams, numerical tables, calculations or omitted formulas may have insufficient evidence.", "Historical examples and figures retain the source's 2018 context and are not current economic facts.", "PDF and printed page numbering differ by 10 pages in these sections.", "Line geometry is pinned to this source and extractor version; a different source file is refused."],
    }


def serialize(passages: list[dict[str, Any]], manifest: dict[str, Any]) -> tuple[str, str]:
    return (
        "".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n" for p in passages),
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/source/Economics2e-LR.pdf")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--check", action="store_true", help="Verify determinism without modifying corpus files")
    args = parser.parse_args()
    try:
        passages = extract_passages(args.source)
        corpus, manifest = serialize(passages, build_manifest(passages))
        outputs = {"passages.jsonl": corpus, "source_manifest.json": manifest}
        if args.check:
            for name, expected in outputs.items():
                if (args.output_dir / name).read_text(encoding="utf-8") != expected:
                    raise ValueError(f"Rebuild differs: {name}")
        else:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, content in outputs.items():
                (args.output_dir / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"{'Verified' if args.check else 'Built'} {len(passages)} original-text passages in {len(SECTIONS)} sections.")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Corpus build failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
