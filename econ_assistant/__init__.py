"""Evidence-based economics tutor core (no UI or credential persistence)."""

from .api import APIConfig, APIConnectionError, APIResponseError, OpenAICompatibleClient
from .models import Passage, PipelineResult, SearchHit, load_passages
from .pipeline import Pipeline
from .retrieval import BM25Retriever, filter_hits, tokenize

__all__ = [
    "APIConfig", "APIConnectionError", "APIResponseError", "OpenAICompatibleClient",
    "Passage", "PipelineResult", "SearchHit", "load_passages", "Pipeline",
    "BM25Retriever", "filter_hits", "tokenize",
]
