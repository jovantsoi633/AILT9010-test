"""Development evidence only. Offline checks do not claim live AI accuracy."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from econ_assistant.api import APIConfig, OpenAICompatibleClient
from econ_assistant.models import load_passages
from econ_assistant.pipeline import Pipeline
from econ_assistant.retrieval import BM25Retriever, filter_hits
from econ_assistant.safety import INSUFFICIENT_MESSAGE, PII_MESSAGE, REFUSAL_MESSAGES

SYNTHETIC_PRIVACY_INPUTS = [
    "Explain demand. My email is learner@example.invalid.",
    "Explain demand. My phone number is +1 202-555-0147.",
    "Explain demand. My student ID is 3035999999.",
]


class NoNetworkClient:
    """A fail-if-called probe for local privacy checks, not an answer simulator."""
    def __init__(self):
        self.attempts = 0

    def complete(self, system, user):
        self.attempts += 1
        raise AssertionError("Local privacy input attempted a model request.")


def hits_json(hits):
    return [{"id": h.passage.id, "score": h.score, "matched_terms": list(h.matched_terms),
             "section": h.passage.section, "pdf_page": h.passage.pdf_page} for h in hits]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--model", default="deepseek-flash")
    args = parser.parse_args(argv)
    corpus_path = ROOT / "data/passages.jsonl"
    settings = json.loads((ROOT / "data/retrieval_config.json").read_text(encoding="utf-8"))
    dev_path = ROOT / "data/development_questions.json"
    development = json.loads(dev_path.read_text(encoding="utf-8"))
    cases = development["questions"]
    retriever = BM25Retriever(load_passages(corpus_path))
    corpus_hash = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    dev_hash = hashlib.sha256(dev_path.read_bytes()).hexdigest()
    if settings.get("corpus_sha256") != corpus_hash or settings.get("development_sha256") != dev_hash:
        parser.error("Corpus or development questions changed since calibration. Run scripts/calibrate.py first.")
    corpus_ids = {p.id for p in retriever.passages}
    case_ids = [c["id"] for c in cases]
    if len(case_ids) != len(set(case_ids)):
        parser.error("Development case IDs must be unique.")
    for case in cases:
        refs = set(case.get("reference_passage_ids", []))
        if case["expected_status"] == "answer" and (not refs or not refs <= corpus_ids):
            parser.error(f"Missing or invalid reference passage IDs for {case['id']}.")
    client = None
    if args.live:
        print("This sends the prescribed synthetic development questions and textbook excerpts to the provider, with up to two requests per question. Provider charges may apply. No final test set is used.")
        key = getpass.getpass("API key (hidden; never written to the report): ").strip()
        if not key:
            parser.error("A key is required for --live. Use --offline without a key.")
        client = OpenAICompatibleClient(APIConfig(api_key=key, base_url=args.base_url, model=args.model))
        del key
    rows = []
    for case in cases:
        expected = case["expected_status"]
        refs = set(case.get("reference_passage_ids", []))
        row = {"id": case["id"], "question": case["question"], "chapter": case.get("chapter"),
               "expected_status": expected, "reference_passage_ids": sorted(refs),
               "reference_answer": case.get("reference_answer", "")}
        if args.live:
            result = Pipeline(retriever, client, settings["tau"]).run(case["question"], chapter=case.get("chapter"))
            raw = retriever.search(result.rewritten_query, chapter=case.get("chapter")) if result.rewritten_query else []
            row.update({"actual_status": result.status, "message": result.message, "answer": result.answer,
                        "decision": result.decision, "rewritten_query": result.rewritten_query,
                        "api_calls": result.api_calls, "top_three": hits_json(raw), "retained": hits_json(result.hits),
                        "status_pass": result.status == expected,
                        "reference_retrieval_hit": refs <= {h.passage.id for h in raw} if refs else None,
                        "required_references_retained": refs <= {h.passage.id for h in result.hits} if refs else None,
                        "manual_answer_review": "PENDING two independent human reviewers" if expected == "answer" else "not applicable"})
            if expected == "refused":
                row["fixed_message_pass"] = result.message == REFUSAL_MESSAGES[case["expected_decision"]]
            elif expected == "insufficient":
                row["fixed_message_pass"] = result.message == INSUFFICIENT_MESSAGE
        elif expected != "refused":
            query = case["retrieval_query"]
            raw = retriever.search(query, chapter=case.get("chapter"))
            kept = filter_hits(raw, query, settings["tau"])
            row.update({"annotated_search_query": query, "top_three": hits_json(raw), "retained": hits_json(kept),
                        "reference_retrieval_hit": refs <= {h.passage.id for h in raw} if refs else None,
                        "required_references_retained": refs <= {h.passage.id for h in kept} if refs else None,
                        "uncovered_filter_pass": not kept if expected == "insufficient" else None,
                        "actual_status": "retrieval_only", "api_calls": 0,
                        "live_answer_and_classification": "NOT TESTED"})
        else:
            row.update({"actual_status": "not_tested_offline", "api_calls": 0,
                        "live_answer_and_classification": "NOT TESTED"})
        rows.append(row)
        print(f"{case['id']}: {row['actual_status']}")
    smoke = []
    for case in development.get("additional_live_smoke_checks", []):
        row = {"id": case["id"], "question": case["question"], "expected_status": case["expected_status"]}
        if args.live:
            result = Pipeline(retriever, client, settings["tau"]).run(case["question"], chapter=case.get("chapter"))
            row.update({"actual_status": result.status, "message": result.message, "answer": result.answer,
                        "rewritten_query": result.rewritten_query, "decision": result.decision,
                        "api_calls": result.api_calls, "retained": hits_json(result.hits),
                        "status_pass": result.status == case["expected_status"]})
            if case["expected_status"] == "refused":
                row["fixed_message_pass"] = result.message == REFUSAL_MESSAGES[case["expected_decision"]]
            else:
                row["manual_answer_review"] = "PENDING two independent human reviewers"
        else:
            row.update({"actual_status": "not_tested_offline", "api_calls": 0})
        smoke.append(row)
    privacy = []
    for text in SYNTHETIC_PRIVACY_INPUTS:
        probe = NoNetworkClient()
        result = Pipeline(retriever, probe, settings["tau"]).run(text)
        privacy.append({"input": text, "expected_status": "pii", "actual_status": result.status,
                        "api_calls": result.api_calls, "observed_client_attempts": probe.attempts,
                        "pass": result.status == "pii" and result.api_calls == probe.attempts == 0 and result.message == PII_MESSAGE})
    source_checks = []
    for chapter, query in [("3", "market equilibrium"), ("5", "price elasticity")]:
        hits = retriever.search(query, chapter=chapter)
        source_checks.append({"chapter": chapter, "input": query, "api_calls": 0, "top_three": hits_json(hits),
                              "pass": bool(hits) and all(h.passage.chapter == chapter for h in hits)})
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
              "mode": "live_development" if args.live else "offline_development",
              "corpus_sha256": corpus_hash, "development_sha256": dev_hash, "tau": settings["tau"],
              "calibration_status": settings["calibration_status"],
              "model": args.model if args.live else None, "base_url": args.base_url if args.live else None,
              "limitations": ["Only 4 in-scope development questions; not a final accuracy estimate.",
                               "Offline annotated keywords do not validate model query rewriting or answer quality.",
                               "Citation label validation does not establish semantic support.",
                               "Independent first-use and two-person answer review require real participants."],
              "cases": rows, "additional_smoke_checks": smoke, "synthetic_privacy": privacy, "source_search": source_checks}
    retrieval_pass = all(r.get("reference_retrieval_hit", True) is not False and
                         r.get("required_references_retained", True) is not False and
                         r.get("uncovered_filter_pass", True) is not False for r in rows)
    local_pass = all(r["pass"] for r in privacy + source_checks)
    live_pass = all(r.get("status_pass", False) and r.get("fixed_message_pass", True) for r in rows + smoke) if args.live else None
    report["automated_checks_pass"] = local_pass and retrieval_pass and (live_pass if args.live else True)
    report["manual_answer_quality_verified"] = False
    output = ROOT / "evidence" / ("development_live.json" if args.live else "development_offline.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Evidence: {output}")
    return 0 if report["automated_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
