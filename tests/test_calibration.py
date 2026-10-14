import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from econ_assistant.models import Passage
from econ_assistant.retrieval import BM25Retriever, filter_hits
from scripts.calibrate import choose_threshold


def passage(identifier, text):
    return Passage(identifier, text, "3", "Demand and Supply", "3.1", "Demand", 58, 48, "https://example.org/source.pdf", "CC BY 4.0")


class CalibrationTests(unittest.TestCase):
    def test_filters_uncovered_without_losing_required_reference(self):
        r = BM25Retriever([passage("definition", "demand quantity demanded price curve"),
                           passage("generic", "ordinary price example")])
        cases = [{"id": "in", "expected_status": "answer", "reference_passage_ids": ["definition"]},
                 {"id": "out", "expected_status": "insufficient"}]
        best, _, _ = choose_threshold(r, cases, {"in": "demand quantity demanded curve", "out": "price deflator"})
        self.assertEqual(best["total_errors"], 0)
        self.assertTrue(filter_hits(r.search("demand quantity demanded curve"), "demand quantity demanded curve", best["tau"]))
        self.assertFalse(filter_hits(r.search("price deflator"), "price deflator", best["tau"]))

    def test_missing_reference_is_not_fixed_by_lowering_threshold(self):
        r = BM25Retriever([passage("ref", "totally separate definition"), passage("hit", "demand price")])
        cases = [{"id": "in", "expected_status": "answer", "reference_passage_ids": ["ref"]}]
        best, _, details = choose_threshold(r, cases, {"in": "demand"})
        self.assertEqual(best["retrieval_failures_before_filter"], 1)
        self.assertEqual(best["in_scope_questions_missing_reference"], 1)
        self.assertFalse(details[0]["reference_retrieval_hit"])

    def test_all_required_passages_must_be_present(self):
        r = BM25Retriever([passage("a", "demand"), passage("b", "other concept")])
        cases = [{"id": "in", "expected_status": "answer", "reference_passage_ids": ["a", "b"]}]
        best, _, _ = choose_threshold(r, cases, {"in": "demand"})
        self.assertEqual(best["total_errors"], 1)

    def test_invalid_references_and_missing_queries_fail(self):
        r = BM25Retriever([passage("a", "demand")])
        case = {"id": "in", "expected_status": "answer", "reference_passage_ids": ["unknown"]}
        with self.assertRaises(ValueError):
            choose_threshold(r, [case], {"in": "demand"})
        with self.assertRaises(ValueError):
            choose_threshold(r, [case], {})


if __name__ == "__main__":
    unittest.main()
