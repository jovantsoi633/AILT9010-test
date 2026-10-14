"""Real Streamlit UI checks over the bundled corpus, with a network guard."""
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def app(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
        self.assertEqual(len(at.exception), 0)
        return at

    @staticmethod
    def click(at, label):
        return next(button for button in at.button if button.label == label).click().run()

    def test_no_key_source_search_retrieves_real_provenance(self):
        at = self.app()
        at.text_area[0].set_value("market equilibrium")
        self.click(at, "Find passages")
        self.assertEqual(len(at.exception), 0)
        hits = at.session_state["last_run"]["hits"]
        self.assertEqual(len(hits), 3)
        self.assertIn("equilibrium", hits[0].passage.text.lower())
        self.assertEqual(hits[0].passage.pdf_page, 61)
        self.assertIn("CC BY 4.0", hits[0].passage.attribution)

    def test_chapter_change_clears_old_results_and_search_stays_in_scope(self):
        at = self.app()
        at.text_area[0].set_value("market equilibrium")
        self.click(at, "Find passages")
        at.selectbox[0].select("5 · Elasticity").run()
        with self.assertRaises(KeyError):
            at.session_state["last_run"]
        at.text_area[0].set_value("price elasticity total revenue")
        self.click(at, "Find passages")
        self.assertTrue(all(h.passage.chapter == "5" for h in at.session_state["last_run"]["hits"]))

    def test_ai_without_key_is_clear_and_search_remains_available(self):
        at = self.app()
        at.radio[0].set_value("AI Q&A").run()
        at.text_area[0].set_value("What is demand?")
        self.click(at, "Explain with evidence")
        self.assertTrue(any("Enter an API key" in w.value for w in at.warning))
        self.assertEqual(len(at.exception), 0)
        at.radio[0].set_value("Source search").run()
        at.text_area[0].set_value("demand")
        self.click(at, "Find passages")
        self.assertTrue(at.session_state["last_run"]["hits"])

    def test_privacy_prevents_network_in_ui_and_clear_key_removes_it(self):
        at = self.app()
        at.radio[0].set_value("AI Q&A").run()
        next(t for t in at.text_input if t.label == "API key").set_value("unit-test-only-key")
        at.text_area[0].set_value("Explain demand. My email is learner@example.invalid.")
        with patch("econ_assistant.api.OpenAICompatibleClient.complete", side_effect=AssertionError("UI attempted network")):
            self.click(at, "Explain with evidence")
        result = at.session_state["last_run"]["result"]
        self.assertEqual(result.status, "pii")
        self.assertEqual(result.api_calls, 0)
        self.assertEqual(len(at.exception), 0)
        self.click(at, "Clear API key")
        self.assertEqual(at.session_state["api_key"], "")
        with self.assertRaises(KeyError):
            at.session_state["last_run"]

    def test_empty_nonenglish_and_no_matching_query_have_readable_feedback(self):
        at = self.app()
        self.click(at, "Find passages")
        self.assertTrue(any("Enter a question" in w.value for w in at.warning))
        at.text_area[0].set_value("需求是什么")
        self.click(at, "Find passages")
        self.assertTrue(any("supports English" in w.value for w in at.warning))
        at.text_area[0].set_value("quuxunmatchabletoken")
        self.click(at, "Find passages")
        self.assertTrue(any("No matching" in w.value for w in at.warning))
        self.assertEqual(len(at.exception), 0)


if __name__ == "__main__":
    unittest.main()
