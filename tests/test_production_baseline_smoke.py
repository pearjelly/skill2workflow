import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.production_baseline_smoke import (
    EVIDENCE_SCHEMA_VERSION,
    WORK_DIR_MARKER,
    WORK_DIR_MARKER_VALUE,
    _normalize_result,
    _reset_work_dir,
    _suite,
    run_baseline,
)


class ProductionBaselineSmokeTests(TestCase):
    def test_suite_is_fixed_bounded_and_uses_redacted_check_names(self):
        with TemporaryDirectory() as temporary:
            work_dir = Path(temporary) / "baseline"
            checks = _suite(work_dir)

        names = [name for name, _command, _child in checks]
        self.assertEqual(len(names), 19)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("service_soak_smoke", names)
        self.assertIn("reproducible_build", names)
        for _name, command, _child in checks:
            self.assertNotIn("AUTH_TOKEN", " ".join(command))
            self.assertNotIn("secret-value", " ".join(command))

    def test_run_baseline_writes_only_public_summary_and_cleans_children(self):
        with TemporaryDirectory() as temporary:
            work_dir = Path(temporary) / "baseline"

            def runner(command, cwd):
                return 0, False

            evidence = run_baseline(work_dir, command_runner=runner)
            self.assertEqual(evidence["schema_version"], EVIDENCE_SCHEMA_VERSION)
            self.assertEqual(evidence["status"], "passed")
            self.assertEqual(evidence["check_count"], 19)
            self.assertEqual(evidence["passed_count"], 19)
            self.assertEqual(
                set(path.name for path in work_dir.iterdir()),
                {WORK_DIR_MARKER, "production-baseline-evidence.json"},
            )
            serialized = json.dumps(evidence, ensure_ascii=False)
            self.assertNotIn(str(work_dir), serialized)
            self.assertEqual(
                json.loads((work_dir / "production-baseline-evidence.json").read_text()),
                evidence,
            )
            self.assertEqual((work_dir / "production-baseline-evidence.json").stat().st_mode & 0o777, 0o644)

    def test_failed_and_timed_out_checks_are_explicit_without_raw_output(self):
        with TemporaryDirectory() as temporary:
            work_dir = Path(temporary) / "baseline"
            calls = []

            def runner(command, cwd):
                calls.append(command)
                return (124, True) if len(calls) == 1 else (1, False)

            evidence = run_baseline(work_dir, command_runner=runner)
            self.assertEqual(evidence["status"], "failed")
            self.assertEqual(evidence["checks"][0]["timed_out"], True)
            self.assertEqual(evidence["checks"][0]["exit_code"], 124)
            self.assertEqual(evidence["checks"][0]["name"], "unit_tests")
            self.assertNotIn("stdout", json.dumps(evidence))

    def test_existing_work_dir_requires_marker(self):
        with TemporaryDirectory() as temporary:
            work_dir = Path(temporary) / "existing"
            work_dir.mkdir()
            with self.assertRaises(ValueError):
                _reset_work_dir(work_dir)
            (work_dir / WORK_DIR_MARKER).write_text(WORK_DIR_MARKER_VALUE, encoding="utf-8")
            _reset_work_dir(work_dir)
            self.assertFalse(work_dir.exists())

    def test_normalize_result_rejects_ambiguous_runner_values(self):
        self.assertEqual(_normalize_result(0), (0, False))
        self.assertEqual(_normalize_result((124, True)), (124, True))
        with self.assertRaises(ValueError):
            _normalize_result("passed")
