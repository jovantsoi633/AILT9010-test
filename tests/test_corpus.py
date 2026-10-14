"""Corpus provenance, scope, and reproducibility checks (no model/API calls)."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_corpus import (
    ATTRIBUTION, DOWNLOAD_LINE, ROOT, SECTIONS, SOURCE_SHA256, SOURCE_URL,
    build_manifest, extract_passages, normalize_lines, serialize, validate_source,
)


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.passages = [json.loads(line) for line in (ROOT / "data/passages.jsonl").read_text(encoding="utf-8").splitlines()]
        cls.by_id = {p["id"]: p for p in cls.passages}
        cls.manifest = json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))

    def test_scope_and_page_locators(self):
        self.assertEqual(len(self.passages), 203)
        self.assertEqual(len(self.by_id), len(self.passages))
        self.assertEqual({p["section"] for p in self.passages}, set(SECTIONS))
        self.assertEqual({p["chapter"] for p in self.passages}, {"3", "5"})
        for p in self.passages:
            with self.subTest(passage=p["id"]):
                self.assertEqual(p["printed_page"], p["pdf_page"] - 10)
                self.assertEqual(p["printed_page_end"], p["pdf_page_end"] - 10)
                self.assertGreaterEqual(p["pdf_page_end"], p["pdf_page"])
                low, high = (56, 84) if p["chapter"] == "3" else (118, 136)
                self.assertLessEqual(low, p["pdf_page"])
                self.assertLessEqual(p["pdf_page_end"], high)
                self.assertEqual(p["section_title"], SECTIONS[p["section"]])

    def test_original_line_spans_and_attribution(self):
        for p in self.passages:
            with self.subTest(passage=p["id"]):
                self.assertEqual(p["source"], SOURCE_URL)
                self.assertEqual(p["attribution"], ATTRIBUTION)
                self.assertIn(DOWNLOAD_LINE, p["attribution"])
                self.assertEqual(normalize_lines([s["text"] for s in p["source_spans"]]), p["text"])
                self.assertEqual(hashlib.sha256(p["text"].encode("utf-8")).hexdigest(), p["text_sha256"])
                self.assertNotIn("Chapter 3 |", p["text"])
                self.assertNotIn("Chapter 5 |", p["text"])
                self.assertNotIn("This OpenStax book is available", p["text"])
                self.assertNotIn("http://openstaxcollege.org", p["text"])
                self.assertFalse(p["text"][0].islower(), "Truncated paragraph start")
                self.assertGreaterEqual(len(p["text"].split()), 16)

    def test_development_reference_evidence_is_present(self):
        expected = {
            "ch3-s3-1-p058-02": ["demand is not the same as quantity demanded", "specific) point on the curve"],
            "ch3-s3-1-p061-08": ["excess demand, or a shortage", "price rises toward the equilibrium level"],
            "ch5-s5-1-p118-01": ["price elasticity of demand is the percentage change", "divided by the percentage change in the price"],
            "ch5-s5-3-p127-02": ["If demand is elastic", "if demand is inelastic", "total revenue will rise"],
        }
        for passage_id, phrases in expected.items():
            for phrase in phrases:
                self.assertIn(phrase, self.by_id[passage_id]["text"])

    def test_out_of_scope_development_topics_have_no_direct_evidence(self):
        body = " ".join(p["text"] for p in self.passages).lower()
        for topic in ("unemployment rate", "gdp deflator", "fractional reserve banking"):
            self.assertNotIn(topic, body)

    def test_manifest_matches_corpus_and_edition(self):
        self.assertEqual(self.manifest, build_manifest(self.passages))
        self.assertEqual(self.manifest["source_sha256"], SOURCE_SHA256)
        self.assertEqual(self.manifest["copyright_page"]["pdf_page"], 4)
        self.assertEqual(self.manifest["original_publication_year"], 2017)
        self.assertEqual(self.manifest["copyright"], "©2018 Rice University")

    def test_changed_source_is_refused_before_extracting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "changed.pdf"
            path.write_bytes(b"not the pinned textbook")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                validate_source(path)

    @unittest.skipUnless((ROOT / "data/source/Economics2e-LR.pdf").is_file(), "Optional pinned source PDF is not downloaded")
    def test_full_rebuild_matches_original_pdf(self):
        rebuilt = extract_passages(ROOT / "data/source/Economics2e-LR.pdf")
        corpus, manifest = serialize(rebuilt, build_manifest(rebuilt))
        self.assertEqual(corpus, (ROOT / "data/passages.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(manifest, (ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
