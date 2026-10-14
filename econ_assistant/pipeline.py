"""The two-call policy/check/retrieve/answer workflow with explicit outcomes."""

from __future__ import annotations

import json
import math
import re
from typing import Protocol

from .api import APIConnectionError, APIResponseError
from .models import PipelineResult
from .prompts import ANSWER_SYSTEM, CLASSIFIER_SYSTEM, answer_payload, classifier_payload
from .retrieval import BM25Retriever, filter_hits, tokenize
from .safety import (
    CONNECTION_MESSAGE, INSUFFICIENT_MESSAGE, PII_MESSAGE, PROTOCOL_MESSAGE,
    REFUSAL_MESSAGES, contains_personal_data, is_english_input,
)


class CompletionClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


def _has_external_markup(answer: str) -> bool:
    """Keep generated prose inert; only the UI may create source links.

    Ordinary emphasis/lists and adjacent passage citations remain available.
    Reject links even when they would render as text without a definition.
    """
    if re.search(r"\b[a-z][a-z0-9+.-]*://|\b(?:data|javascript|vbscript|mailto|tel|file):|\bwww\.", answer, re.I):
        return True
    if re.search(r"(?<![\w:])//[a-z0-9]|\b(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}\b", answer, re.I):
        return True
    if re.search(r"!\s*\[|\[[^\]]*\]\s*\(|^\s{0,3}\[[^\]]+\]:\s*\S", answer, re.M):
        return True
    if re.search(r"<!--|<!DOCTYPE\b|<\?|<\s*/?\s*[a-z][^<>]*>", answer, re.I):
        return True
    for match in re.finditer(r"(?=(\[[^\]]*\])\s*(\[[^\]]*\]))", answer):
        if not all(re.fullmatch(r"\[P[1-9]\d*\]", label) for label in match.groups()):
            return True
    return False


def _json_object(text: str) -> dict:
    if not isinstance(text, str) or len(text) > 16_000:
        raise ValueError("Invalid output.")
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.I)
        stripped = stripped[:-3].strip()
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("Expected an object.")
    return value


class Pipeline:
    def __init__(self, retriever: BM25Retriever, client: CompletionClient, tau: float):
        if not math.isfinite(tau) or tau < 0:
            raise ValueError("tau must be a calibrated, finite non-negative number.")
        self.retriever, self.client, self.tau = retriever, client, tau

    def run(self, question: str, chapter: str | None = None) -> PipelineResult:
        question = question.strip()
        if not question or len(question) > 2_000:
            return PipelineResult("input_error", "Enter an English question of 1-2,000 characters.")
        stages = ["Local privacy check"]
        if contains_personal_data(question):
            return PipelineResult("pii", PII_MESSAGE, stages=tuple(stages))
        if not is_english_input(question):
            return PipelineResult("input_error", "Please enter your economics question in English.", stages=tuple(stages))
        if chapter is not None and str(chapter) not in {value[0] for value in self.retriever.chapters}:
            return PipelineResult("input_error", "Select one of the available textbook chapters.", stages=tuple(stages))

        stages.append("Request check and search rewrite")
        calls = 1
        try:
            checked = _json_object(self.client.complete(CLASSIFIER_SYSTEM, classifier_payload(question)))
            decision = checked.get("decision")
            if decision not in ("allow", *REFUSAL_MESSAGES):
                raise ValueError("Unknown decision.")
            query = checked.get("query", "")
            if not isinstance(query, str) or len(query) > 512:
                raise ValueError("Invalid query.")
            if decision == "allow" and (not tokenize(query) or not is_english_input(query)):
                raise ValueError("Missing English query.")
        except APIConnectionError:
            return PipelineResult("connection_error", CONNECTION_MESSAGE, api_calls=calls, stages=tuple(stages))
        except (APIResponseError, ValueError, TypeError):
            return PipelineResult("protocol_error", PROTOCOL_MESSAGE, api_calls=calls, stages=tuple(stages))

        if decision != "allow":
            return PipelineResult(
                "refused", REFUSAL_MESSAGES[decision], api_calls=calls,
                decision=decision, stages=tuple(stages),
            )

        stages.append("Top-three textbook search and relevance filter")
        hits = tuple(filter_hits(self.retriever.search(query, chapter=chapter, top_k=3), query, self.tau))
        metadata = dict(hits=hits, rewritten_query=query, decision=decision)
        if not hits:
            return PipelineResult("insufficient", INSUFFICIENT_MESSAGE, api_calls=calls, stages=tuple(stages), **metadata)

        stages.append("Evidence-based explanation")
        calls = 2
        try:
            response = _json_object(self.client.complete(ANSWER_SYSTEM, answer_payload(question, hits)))
            if type(response.get("sufficient")) is not bool:
                raise ValueError("Missing sufficiency decision.")
            if not response["sufficient"]:
                return PipelineResult("insufficient", INSUFFICIENT_MESSAGE, api_calls=calls, stages=tuple(stages), **metadata)
            answer = response.get("answer")
            if not isinstance(answer, str) or not answer.strip() or len(answer) > 5_000:
                raise ValueError("Invalid answer.")
            if _has_external_markup(answer):
                raise ValueError("External links or markup are not supported in model answers.")
            labels = tuple(dict.fromkeys(re.findall(r"\[P[^\]\r\n]*\]", answer, flags=re.I)))
            valid_labels = {f"[P{index}]" for index in range(1, len(hits) + 1)}
            if not labels or any(label not in valid_labels for label in labels):
                raise ValueError("Unverifiable citation.")
        except APIConnectionError:
            return PipelineResult("connection_error", CONNECTION_MESSAGE, api_calls=calls, stages=tuple(stages), **metadata)
        except (APIResponseError, ValueError, TypeError):
            return PipelineResult("protocol_error", PROTOCOL_MESSAGE, api_calls=calls, stages=tuple(stages), **metadata)

        stages.append("Citation validation")
        return PipelineResult(
            "answer", "Explanation based on the selected textbook passages.",
            answer=answer.strip(), api_calls=calls, stages=tuple(stages),
            citation_labels=labels, **metadata,
        )
