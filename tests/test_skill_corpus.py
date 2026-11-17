import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.skill_corpus_benchmark import ROOT, benchmark, main


class SkillCorpusTests(TestCase):
    def test_original_corpus_covers_english_chinese_and_explicit_controls(self):
        result = benchmark(ROOT / "tests/fixtures/skill_corpus")
        self.assertGreaterEqual(result["skills"], 20)
        self.assertLessEqual(result["skills"], 50)
        self.assertEqual(result["inference_accuracy"], 1)
        self.assertEqual(result["false_human_gates"], 0)
        self.assertGreaterEqual(result["enforced_node_ratio"], 0.25)
        self.assertEqual(result["mismatches"], [])

    def test_wrong_expectation_fails_the_ci_gate(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text("## Steps\n1. Ask user for approval\n")
            (root / "expectations.json").write_text(json.dumps({
                "cases": [{"path": "SKILL.md", "types": ["step"]}],
            }))
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--corpus", str(root)]), 1)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["inference_accuracy"], 0)
            self.assertEqual(result["false_human_gates"], 1)
            self.assertFalse(result["passed"])
