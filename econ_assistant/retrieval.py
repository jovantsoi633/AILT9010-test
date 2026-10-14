"""Deterministic lexical retrieval; no model, network, or external index needed."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable

from .models import Passage, SearchHit


# Keep content-bearing terms such as "own", "less", "increase", and "not".
STOPWORDS = frozenset("""
a an the and or but if then than as at by for from in into of on onto to with
without about above below between through during before after against among
is are was were be been being am do does did doing have has had having
i me my mine we us our ours you your yours he him his she her hers it its
they them their theirs this that these those who whom which what where when
why how can could may might shall should will would please explain tell
give show describe mean means meaning example examples question
""".split())
_TOKEN = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", re.ASCII)


def tokenize(text: str) -> tuple[str, ...]:
    """Lowercase English words, excluding stopwords and purely numeric tokens."""
    tokens = _TOKEN.findall(text.lower().replace("’", "'"))
    return tuple(token for token in tokens if token not in STOPWORDS and token[0].isalpha())


class BM25Retriever:
    """BM25 over the complete corpus, then a chapter filter before ranking.

    The IDF/length statistics stay fixed across chapter selections, so the same
    calibrated threshold has the same meaning in either UI selection.
    """

    def __init__(self, passages: Iterable[Passage], k1: float = 1.5, b: float = 0.75):
        self.passages = tuple(passages)
        if not self.passages:
            raise ValueError("Cannot index an empty corpus.")
        if len({passage.id for passage in self.passages}) != len(self.passages):
            raise ValueError("Passage IDs must be unique.")
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("Invalid BM25 parameters.")
        self.k1, self.b = k1, b
        self._counts = tuple(Counter(tokenize(passage.text)) for passage in self.passages)
        self._lengths = tuple(sum(count.values()) for count in self._counts)
        self._avg_length = sum(self._lengths) / len(self._lengths) or 1.0
        document_frequency: Counter[str] = Counter()
        for counts in self._counts:
            document_frequency.update(counts.keys())
        count = len(self.passages)
        self._idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    @property
    def chapters(self) -> tuple[tuple[str, str], ...]:
        """Unique (chapter ID, title) pairs in original corpus order."""
        return tuple(dict.fromkeys((p.chapter, p.chapter_title) for p in self.passages))

    def search(self, query: str, chapter: str | None = None, top_k: int = 3) -> list[SearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        terms = tuple(sorted(set(tokenize(query))))
        if not terms:
            return []
        hits = []
        for passage, counts, length in zip(self.passages, self._counts, self._lengths):
            if chapter is not None and passage.chapter != str(chapter):
                continue
            matched = tuple(term for term in terms if counts.get(term, 0))
            if not matched:
                continue
            normalization = self.k1 * (1 - self.b + self.b * length / self._avg_length)
            score = sum(
                self._idf[term] * counts[term] * (self.k1 + 1) / (counts[term] + normalization)
                for term in matched
            )
            hits.append(SearchHit(passage=passage, score=score, matched_terms=matched))
        hits.sort(key=lambda hit: (-hit.score, hit.passage.id))
        return hits[:top_k]


def filter_hits(hits: Iterable[SearchHit], query: str, tau: float) -> list[SearchHit]:
    """Keep top-k hits with score >= tau and at least one query content word."""
    if not math.isfinite(tau) or tau < 0:
        raise ValueError("tau must be a finite non-negative number.")
    terms = set(tokenize(query))
    return [
        hit for hit in hits
        if hit.score >= tau and terms.intersection(tokenize(hit.passage.text))
    ]
