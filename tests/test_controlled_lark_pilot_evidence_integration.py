import json
import os
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.controlled_lark_pilot import (
    finalize_pilot,
    generate_pilot_evidence,
    initialize_pilot,
)

from tests.test_controlled_lark_pilot_evidence import (
    NOW,
    _build_ready_state,
    _prepare_repo,
    _valid_charter,
    _valid_decision,
)


def _json_bytes_map(directory):
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*.json"))
    }


class ControlledLarkPilotEvidenceIntegrationTests(TestCase):
    def test_finalize_rejects_incomplete_evidence_before_any_write(self):
        expected_unmet = (
            "approved_live_runs_threshold, distinct_calendar_days_threshold, "
            "distinct_private_cases_threshold, human_rejection, "
            "disabled_live_exercise, rollback_exercise, verification"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root = _prepare_repo(root)
            work_dir = root / "pilot"
            initialize_pilot(repo_root, work_dir, _valid_charter(), now=NOW)
            requested = repo_root / "docs" / "pilot-evidence" / "loop-40"

            with self.assertRaisesRegex(
                ValueError,
                expected_unmet,
            ):
                finalize_pilot(
                    repo_root,
                    work_dir,
                    _valid_decision(),
                    output_dir=requested,
                    now=NOW,
                )

            self.assertEqual(list((work_dir / "evidence").iterdir()), [])
            self.assertFalse((work_dir / "private" / "decision.json").exists())
            self.assertFalse(
                (work_dir / "private" / "finalization.json").exists()
            )
            self.assertFalse(requested.exists())

    def test_finalize_rejects_invalid_or_private_decisions_before_any_write(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, _transport = _build_ready_state(root)
            (work_dir / "private" / "decision.json").unlink()
            requested = repo_root / "docs" / "pilot-evidence" / "loop-40"
            invalid_decisions = []
            for key, value in (
                ("decision", "ship"),
                ("partner_acknowledged", False),
                ("operator_acknowledged", False),
                ("commercial_engagement_confirmed", False),
                ("partner_acknowledged", 1),
                ("rationale", ""),
                ("rationale", "   "),
                ("rationale", "Private Account case-001 was successful."),
            ):
                candidate = _valid_decision()
                candidate[key] = value
                invalid_decisions.append(candidate)
            missing = _valid_decision()
            del missing["schema_version"]
            invalid_decisions.append(missing)
            extra = _valid_decision()
            extra["customer_name"] = "Private Account"
            invalid_decisions.append(extra)

            for candidate in invalid_decisions:
                with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                    finalize_pilot(
                        repo_root,
                        work_dir,
                        candidate,
                        output_dir=requested,
                        now=NOW,
                    )
                self.assertEqual(list((work_dir / "evidence").iterdir()), [])
                self.assertFalse(
                    (work_dir / "private" / "decision.json").exists()
                )
                self.assertFalse(
                    (work_dir / "private" / "finalization.json").exists()
                )
                self.assertFalse(requested.exists())

    def test_finalize_writes_equivalent_private_and_requested_packs_then_marker(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, _transport = _build_ready_state(root)
            (work_dir / "private" / "decision.json").unlink()
            requested = repo_root / "docs" / "pilot-evidence" / "loop-40"
            decision = _valid_decision()

            result = finalize_pilot(
                repo_root,
                work_dir,
                decision,
                output_dir=requested,
                now=NOW,
            )

            private_pack = _json_bytes_map(work_dir / "evidence")
            requested_pack = _json_bytes_map(requested)
            persisted_decision = json.loads(
                (work_dir / "private" / "decision.json").read_text(
                    encoding="utf-8"
                )
            )
            marker_path = work_dir / "private" / "finalization.json"
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            decision_mode = (
                work_dir / "private" / "decision.json"
            ).stat().st_mode & 0o077
            marker_mode = marker_path.stat().st_mode & 0o077
            encoded = b"".join(requested_pack.values()) + json.dumps(result).encode()

            self.assertEqual(private_pack, requested_pack)
            self.assertEqual(persisted_decision, decision)
            self.assertEqual(
                marker,
                {
                    "schema_version": "controlled-lark-pilot-finalization-0.1.0",
                    "finalized": True,
                    "decision": "continue",
                    "finalized_at": "2026-07-23T17:00:00+08:00",
                },
            )
            self.assertEqual(decision_mode, 0)
            self.assertEqual(marker_mode, 0)
            self.assertEqual(
                result,
                {
                    "status": "finalized",
                    "decision": "continue",
                    "approved_live_runs": 5,
                    "distinct_calendar_days": 5,
                    "distinct_private_cases": 2,
                    "rejected_runs": 1,
                    "output_dir": str(requested),
                },
            )
            for forbidden in (
                "case-001",
                "case-002",
                "case-rejected",
                "Private Account",
                "Private Risk",
                "ou_private",
                "private-token",
                "private-provider-message",
                "private-task-guid",
            ):
                self.assertNotIn(forbidden.encode("utf-8"), encoded)

            stale = requested / "stale.json"
            stale.write_text("{}", encoding="utf-8")
            regenerated = generate_pilot_evidence(
                repo_root,
                work_dir,
                output_dir=requested,
                now=NOW + timedelta(seconds=1),
            )
            self.assertEqual(regenerated["output_dir"], str(requested))
            self.assertFalse(stale.exists())
            self.assertEqual(
                json.loads(
                    (requested / "decision.json").read_text(encoding="utf-8")
                ),
                decision,
            )

    def test_finalize_allows_external_export_but_rejects_other_repository_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, _transport = _build_ready_state(root)
            (work_dir / "private" / "decision.json").unlink()
            wrong = repo_root / "docs" / "pilot-evidence" / "other"

            with self.assertRaisesRegex(ValueError, "repository evidence output"):
                finalize_pilot(
                    repo_root,
                    work_dir,
                    _valid_decision(),
                    output_dir=wrong,
                    now=NOW,
                )

            self.assertEqual(list((work_dir / "evidence").iterdir()), [])
            self.assertFalse(wrong.exists())
            self.assertFalse((work_dir / "private" / "decision.json").exists())
            self.assertFalse(
                (work_dir / "private" / "finalization.json").exists()
            )

            external = root / "shared-redacted-evidence"
            finalized = finalize_pilot(
                repo_root,
                work_dir,
                _valid_decision(),
                output_dir=external,
                now=NOW,
            )
            self.assertEqual(finalized["output_dir"], str(external))
            self.assertEqual(
                _json_bytes_map(work_dir / "evidence"),
                _json_bytes_map(external),
            )

    def test_finalize_rejects_declared_repo_symlink_before_private_pack_write(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, _transport = _build_ready_state(root)
            (work_dir / "private" / "decision.json").unlink()
            outside = root / "outside-output"
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("sentinel", encoding="utf-8")
            linked_parent = repo_root / "docs" / "pilot-evidence"
            linked_parent.mkdir(parents=True)
            linked = linked_parent / "wrong"
            linked.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "repository evidence output"):
                finalize_pilot(
                    repo_root,
                    work_dir,
                    _valid_decision(),
                    output_dir=linked,
                    now=NOW,
                )

            self.assertEqual(list((work_dir / "evidence").iterdir()), [])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertFalse((work_dir / "private" / "decision.json").exists())
            self.assertFalse(
                (work_dir / "private" / "finalization.json").exists()
            )

    def test_finalize_write_failure_never_leaves_decision_or_marker(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, _transport = _build_ready_state(root)
            (work_dir / "private" / "decision.json").unlink()
            requested = root / "requested-evidence"
            writes = []

            def failing_second_write(output_dir, pack):
                writes.append(Path(output_dir))
                if len(writes) == 2:
                    raise OSError("requested export failed")
                return {
                    "status": "written",
                    "file_count": 1,
                    "output_dir": str(output_dir),
                }

            with patch(
                "skill2workflow.controlled_lark_pilot.write_evidence_pack",
                side_effect=failing_second_write,
            ), self.assertRaisesRegex(OSError, "requested export failed"):
                finalize_pilot(
                    repo_root,
                    work_dir,
                    _valid_decision(),
                    output_dir=requested,
                    now=NOW,
                )

            self.assertEqual(writes, [work_dir / "evidence", requested])
            self.assertFalse((work_dir / "private" / "decision.json").exists())
            self.assertFalse(
                (work_dir / "private" / "finalization.json").exists()
            )

    def test_finalize_rejects_static_private_decision_or_marker_symlink_before_pack_write(self):
        for artifact in ("decision.json", "finalization.json"):
            with self.subTest(artifact=artifact), TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                repo_root, work_dir, _transport = _build_ready_state(root)
                decision_path = work_dir / "private" / "decision.json"
                decision_path.unlink()
                target = root / f"outside-{artifact}"
                target.write_text("sentinel", encoding="utf-8")
                linked = work_dir / "private" / artifact
                linked.symlink_to(target)

                with self.assertRaisesRegex(
                    ValueError,
                    "symbolic link|regular file",
                ):
                    finalize_pilot(
                        repo_root,
                        work_dir,
                        _valid_decision(),
                        output_dir=root / "requested",
                        now=NOW,
                    )

                self.assertEqual(list((work_dir / "evidence").iterdir()), [])
                self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")
                self.assertTrue(linked.is_symlink())

    def test_generate_evidence_from_real_sqlite_state_is_redacted_stable_and_ready(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, transport = _build_ready_state(root)
            with patch.dict(
                os.environ,
                {"LARK_BOT_ACCESS_TOKEN": "private-token"},
                clear=True,
            ):
                result = generate_pilot_evidence(repo_root, work_dir, now=NOW)

            evidence_dir = work_dir / "evidence"
            index = json.loads(
                (evidence_dir / "evidence-index.json").read_text(encoding="utf-8")
            )
            run_files = sorted((evidence_dir / "runs").glob("*.json"))
            runs = [json.loads(path.read_text(encoding="utf-8")) for path in run_files]
            encoded = "".join(
                path.read_text(encoding="utf-8")
                for path in evidence_dir.rglob("*.json")
            )
            native_tokens = [
                json.loads(request.data.decode("utf-8"))["client_token"]
                for request, _timeout in transport.calls
            ]

            self.assertEqual(result["output_dir"], str(evidence_dir))
            self.assertEqual(result["run_count"], 6)
            self.assertEqual(result["distinct_private_cases"], 2)
            self.assertEqual(result["unmet_conditions"], [])
            self.assertTrue(index["ready_to_finalize"])
            self.assertEqual(index["approved_live_runs"], 5)
            self.assertEqual(index["distinct_calendar_days"], 5)
            self.assertEqual(index["rejected_runs"], 1)
            self.assertEqual(index["generated_at"], "2026-07-23T17:00:00+08:00")
            self.assertEqual(len(run_files), 6)
            self.assertEqual(
                [(run["started_at"], run["run_id"]) for run in runs],
                sorted((run["started_at"], run["run_id"]) for run in runs),
            )
            self.assertEqual(len(transport.calls), 5)
            for forbidden in (
                "case-001",
                "case-002",
                "case-rejected",
                "Private Account",
                "Private Risk",
                "ou_private",
                "private-token",
                "private-provider-message",
                "private-task-guid",
                *native_tokens,
            ):
                self.assertNotIn(forbidden, encoded)
                self.assertNotIn(forbidden, json.dumps(result))

            finalization = work_dir / "private" / "finalization.json"
            repo_output = repo_root / "docs" / "pilot-evidence" / "loop-40"
            valid_marker = {
                "schema_version": "controlled-lark-pilot-finalization-0.1.0",
                "finalized": True,
                "decision": "continue",
                "finalized_at": "2026-07-23T17:00:00+08:00",
            }
            marker_target = root / "outside-finalization.json"
            marker_target.write_text(json.dumps(valid_marker), encoding="utf-8")
            finalization.symlink_to(marker_target)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=repo_output,
                    now=NOW,
                )
            self.assertEqual(
                json.loads(marker_target.read_text(encoding="utf-8")), valid_marker
            )
            self.assertFalse(repo_output.exists())
            finalization.unlink()

            finalization.mkdir()
            with self.assertRaisesRegex(ValueError, "regular file"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=repo_output,
                    now=NOW,
                )
            self.assertFalse(repo_output.exists())
            finalization.rmdir()

            invalid_markers = [
                {**valid_marker, "finalized": 1},
                {**valid_marker, "decision": "defer"},
                {**valid_marker, "finalized_at": "2026-07-23T17:00:00"},
            ]
            for marker in invalid_markers:
                finalization.write_text(json.dumps(marker), encoding="utf-8")
                with self.subTest(marker=marker), self.assertRaises(ValueError):
                    generate_pilot_evidence(
                        repo_root,
                        work_dir,
                        output_dir=repo_output,
                        now=NOW,
                    )
                self.assertFalse(repo_output.exists())

            finalization.write_text(json.dumps(valid_marker), encoding="utf-8")
            exported = generate_pilot_evidence(
                repo_root,
                work_dir,
                output_dir=repo_output,
                now=NOW,
            )
            self.assertEqual(exported["output_dir"], str(repo_output))
            self.assertTrue((repo_output / "evidence-index.json").is_file())

    def test_generate_evidence_allows_external_explicit_output_without_finalization(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root = _prepare_repo(root)
            work_dir = root / "pilot"
            initialize_pilot(repo_root, work_dir, _valid_charter(), now=NOW)
            output = root / "external-evidence"

            result = generate_pilot_evidence(
                repo_root,
                work_dir,
                output_dir=output,
                now=NOW,
            )

            self.assertEqual(result["output_dir"], str(output))
            self.assertEqual(result["run_count"], 0)
            self.assertTrue((output / "pilot-charter.json").is_file())
            self.assertFalse((work_dir / "private" / "finalization.json").exists())

    def test_generate_evidence_rejects_unfinalized_or_wrong_repository_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root = _prepare_repo(root)
            work_dir = root / "pilot"
            initialize_pilot(repo_root, work_dir, _valid_charter(), now=NOW)
            exact = repo_root / "docs" / "pilot-evidence" / "loop-40"

            with self.assertRaisesRegex(ValueError, "finalization"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=exact,
                    now=NOW,
                )
            with self.assertRaisesRegex(ValueError, "repository evidence output"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=repo_root / "docs" / "pilot-evidence" / "other",
                    now=NOW,
                )

            self.assertFalse(exact.exists())

    def test_repository_export_rejects_marker_swapped_to_symlink_before_open(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, _transport = _build_ready_state(root)
            finalization = work_dir / "private" / "finalization.json"
            valid_marker = {
                "schema_version": "controlled-lark-pilot-finalization-0.1.0",
                "finalized": True,
                "decision": "continue",
                "finalized_at": "2026-07-23T17:00:00+08:00",
            }
            finalization.write_text(json.dumps(valid_marker), encoding="utf-8")
            original_marker = root / "original-finalization.json"
            outside_marker = root / "outside-finalization.json"
            outside_marker.write_text(json.dumps(valid_marker), encoding="utf-8")
            output = repo_root / "docs" / "pilot-evidence" / "loop-40"
            real_exists = Path.exists
            real_open = os.open
            swapped = []

            def racing_exists(path):
                if Path(path) == finalization and not swapped:
                    finalization.rename(original_marker)
                    finalization.symlink_to(outside_marker)
                    swapped.append(True)
                return real_exists(path)

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                if os.fspath(path) == "finalization.json" and not swapped:
                    finalization.rename(original_marker)
                    finalization.symlink_to(outside_marker)
                    swapped.append(True)
                if dir_fd is None:
                    return real_open(path, flags, mode)
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with patch.object(
                Path,
                "exists",
                autospec=True,
                side_effect=racing_exists,
            ), patch.object(os, "open", side_effect=racing_open), self.assertRaisesRegex(
                ValueError,
                "symbolic link|regular file",
            ):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=output,
                    now=NOW,
                )

            self.assertEqual(swapped, [True])
            self.assertEqual(
                json.loads(outside_marker.read_text(encoding="utf-8")), valid_marker
            )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    import unittest

    unittest.main()
