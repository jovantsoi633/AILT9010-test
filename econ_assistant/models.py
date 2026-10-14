"""Small, serializable data structures shared by the UI and evaluation scripts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class Passage:
    id: str
    text: str
    chapter: str
    chapter_title: str
    section: str
    section_title: str
    pdf_page: int
    printed_page: int | str | None
    source: str
    attribution: str
    pdf_page_end: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Passage":
        if not isinstance(value, dict):
            raise ValueError("Each passage must be an object.")
        strings = ("id", "text", "chapter_title", "section_title", "source", "attribution")
        for key in strings:
            if not isinstance(value.get(key), str) or not value[key].strip():
                raise ValueError(f"Passage has a missing or empty {key}.")
        for key in ("chapter", "section"):
            if type(value.get(key)) not in (str, int) or not str(value[key]).strip():
                raise ValueError(f"Passage has a missing {key}.")
        page = value.get("pdf_page")
        end = value.get("pdf_page_end")
        if type(page) is not int or page < 1:
            raise ValueError("pdf_page must be a positive one-based page number.")
        if end is not None and (type(end) is not int or end < page):
            raise ValueError("pdf_page_end must be at least pdf_page.")
        printed = value.get("printed_page")
        if printed is not None and type(printed) not in (int, str):
            raise ValueError("printed_page must be an integer, string, or null.")
        return cls(
            **{key: value[key] for key in strings},
            chapter=str(value["chapter"]), section=str(value["section"]),
            pdf_page=page, pdf_page_end=end, printed_page=printed,
        )


def load_passages(path: str | Path) -> list[Passage]:
    """Read UTF-8 JSONL, a JSON list, or an object containing ``passages``."""
    path = Path(path)
    with path.open(encoding="utf-8-sig") as handle:
        if path.suffix.lower() == ".jsonl":
            rows = [json.loads(line) for line in handle if line.strip()]
        else:
            payload = json.load(handle)
            rows = payload.get("passages") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("The corpus must contain a non-empty passages list.")
    passages = [Passage.from_dict(row) for row in rows]
    if len({passage.id for passage in passages}) != len(passages):
        raise ValueError("Passage IDs must be unique.")
    return passages


@dataclass(frozen=True)
class SearchHit:
    passage: Passage
    score: float
    matched_terms: tuple[str, ...] = ()


Status = Literal[
    "answer", "refused", "pii", "insufficient", "connection_error",
    "protocol_error", "input_error",
]


@dataclass(frozen=True)
class PipelineResult:
    status: Status
    message: str
    answer: str = ""
    hits: tuple[SearchHit, ...] = ()
    api_calls: int = 0
    rewritten_query: str = ""
    decision: str = ""
    stages: tuple[str, ...] = ()
    # Only citations that survived validation; labels map to the hits in order.
    citation_labels: tuple[str, ...] = field(default_factory=tuple)
