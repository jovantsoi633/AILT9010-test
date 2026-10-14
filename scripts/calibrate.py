"""Choose tau on development questions; never read a frozen final test set."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from econ_assistant.models import load_passages
from econ_assistant.retrieval import BM25Retriever, filter_hits


def choose_threshold(retriever, cases, queries):
    """Minimize question-level errors; ties prefer in-scope recall, then lower tau."""
    observations = []
    candidates = {0.0}
    corpus_ids = {p.id for p in retriever.passages}
    for case in cases:
        if case["expected_status"] not in ("answer", "insufficient"):
            continue
        query = queries.get(case["id"], "")
        if not query:
            raise ValueError(f"No usable development search query for {case['id']}.")
        references = set(case.get("reference_passage_ids", []))
        if case["expected_status"] == "answer" and (not references or not references <= corpus_ids):
            raise ValueError(f"Missing or invalid textbook references for {case['id']}.")
        hits = retriever.search(query, chapter=case.get("chapter"), top_k=3)
        for hit in hits:
            candidates.add(hit.score)
            candidates.add(math.nextafter(hit.score, math.inf))
        observations.append((case, query, references, hits))
    if not observations:
        raise ValueError("No development observations to calibrate.")
    results = []
    for tau in sorted(candidates):
        missed, leaked, retrieval_failures = 0, 0, 0
        for case, query, refs, hits in observations:
            raw = {h.passage.id for h in hits}
            kept = {h.passage.id for h in filter_hits(hits, query, tau)}
            if case["expected_status"] == "answer":
                retrieval_failures += int(not refs <= raw)
                missed += int(not refs <= kept)
            else:
                leaked += int(bool(kept))
        results.append({"tau": tau, "total_errors": missed + leaked,
                        "in_scope_questions_missing_reference": missed,
                        "uncovered_questions_retaining_passages": leaked,
                        "retrieval_failures_before_filter": retrieval_failures})
    best = min(results, key=lambda r: (r["total_errors"], r["in_scope_questions_missing_reference"], r["tau"]))
    details = []
    for case, query, refs, hits in observations:
        kept = {h.passage.id for h in filter_hits(hits, query, best["tau"])}
        details.append({"id": case["id"], "query": query, "expected_status": case["expected_status"],
                        "references": sorted(refs), "top_three": [
                            {"id": h.passage.id, "score": h.score,
                             "matched_terms": list(h.matched_terms), "retained": h.passage.id in kept}
                            for h in hits],
                        "reference_retrieval_hit": refs <= {h.passage.id for h in hits} if refs else None})
    return best, results, details


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-results", type=Path, help="Use actual query rewrites from a live development evaluation.")
    args = parser.parse_args(argv)
    corpus_path = ROOT / "data/passages.jsonl"
    dev_path = ROOT / "data/development_questions.json"
    cases = json.loads(dev_path.read_text(encoding="utf-8"))["questions"]
    retriever = BM25Retriever(load_passages(corpus_path))
    dev_hash = hashlib.sha256(dev_path.read_bytes()).hexdigest()
    source = "annotated_keywords"
    if args.live_results:
        live = json.loads(args.live_results.read_text(encoding="utf-8"))
        if live.get("mode") != "live_development":
            parser.error("--live-results must contain a real live_development run.")
        if live.get("corpus_sha256") != hashlib.sha256(corpus_path.read_bytes()).hexdigest():
            parser.error("Live results use a different corpus; rerun the development evaluation first.")
        if live.get("development_sha256") != dev_hash:
            parser.error("Live results use different development questions; rerun the development evaluation first.")
        ids = [r["id"] for r in live["cases"]]
        if len(ids) != len(set(ids)) or set(ids) != {c["id"] for c in cases}:
            parser.error("Live results must contain each current development case exactly once.")
        queries = {r["id"]: r.get("rewritten_query", "") for r in live["cases"]}
        source = "live_development_rewrites"
    else:
        queries = {c["id"]: c.get("retrieval_query", "") for c in cases}
    best, candidates, details = choose_threshold(retriever, cases, queries)
    now = datetime.now(timezone.utc).isoformat()
    report = {"created_at_utc": now, "mode": source,
              "note": "Annotated keyword calibration is provisional until actual model rewrites are checked. Reference misses before filtering cannot be repaired by lowering tau.",
              "selection_rule": "Fewest question-level errors; then fewest in-scope misses; then lowest tau.",
              "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
              "development_sha256": dev_hash,
              "selected": best, "candidates": candidates, "cases": details}
    output = ROOT / "evidence/calibration.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    config = {"tau": best["tau"], "k1": 1.5, "b": 0.75,
              "calibration_status": "provisional_annotated" if not args.live_results else "live_development",
              "calibration_evidence": "evidence/calibration.json", "corpus_sha256": report["corpus_sha256"],
              "development_sha256": dev_hash}
    (ROOT / "data/retrieval_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected": best, "mode": source, "evidence": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
