import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.controlled_lark_pilot_evidence import (
    build_acceptance_summary,
    write_evidence_pack,
)
from skill2workflow._controlled_lark_pilot_evidence_writer import (
    read_json_anchored,
    write_private_json_anchored,
)

from tests.test_controlled_lark_pilot_evidence import _valid_pack


class ControlledLarkPilotEvidenceWriterTests(TestCase):
    def test_write_pack_retries_transient_finish_cleanup_after_durable_commit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            writer = __import__(
                "skill2workflow._controlled_lark_pilot_evidence_writer",
                fromlist=["_remove_tree_at"],
            )
            real_remove = writer._remove_tree_at
            failures = []

            def fail_once(parent_fd, name):
                if name.endswith(".txn") and not failures:
                    failures.append(name)
                    raise OSError("transient finish cleanup failure")
                return real_remove(parent_fd, name)

            with patch.object(writer, "_remove_tree_at", side_effect=fail_once):
                result = write_evidence_pack(output, _valid_pack())

            self.assertEqual(
                result,
                {
                    "status": "written",
                    "file_count": 13,
                    "output_dir": str(output),
                },
            )
            self.assertEqual(len(failures), 1)
            self.assertEqual(
                [path for path in root.iterdir() if path.name.endswith(".txn")],
                [],
            )
            self.assertTrue((output / "evidence-index.json").is_file())

    def test_write_pack_persistent_finish_cleanup_keeps_durable_success(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            writer = __import__(
                "skill2workflow._controlled_lark_pilot_evidence_writer",
                fromlist=["_remove_tree_at"],
            )
            real_remove = writer._remove_tree_at
            failures = []

            def fail_transaction_cleanup(parent_fd, name):
                if name.endswith(".txn"):
                    failures.append(name)
                    raise OSError("persistent finish cleanup failure")
                return real_remove(parent_fd, name)

            with patch.object(
                writer,
                "_remove_tree_at",
                side_effect=fail_transaction_cleanup,
            ):
                result = write_evidence_pack(output, _valid_pack())

            residual = [
                path for path in root.iterdir() if path.name.endswith(".txn")
            ]
            self.assertEqual(result["status"], "written")
            self.assertEqual(result["output_dir"], str(output))
            self.assertGreaterEqual(len(failures), 2)
            self.assertEqual(len(residual), 1)
            self.assertEqual(residual[0].stat().st_mode & 0o077, 0)
            self.assertTrue((output / "evidence-index.json").is_file())

    def test_anchored_json_reader_rejects_fifo_without_blocking(self):
        with TemporaryDirectory() as tmp:
            fifo = Path(tmp).resolve() / "private.json"
            os.mkfifo(fifo, 0o600)
            script = (
                "from pathlib import Path; "
                "from skill2workflow._controlled_lark_pilot_evidence_writer "
                "import read_json_anchored; "
                f"path = Path({str(fifo)!r}); "
                "\ntry:\n read_json_anchored(path)"
                "\nexcept ValueError as error:\n print(str(error)); raise SystemExit(0)"
                "\nraise SystemExit(2)"
            )
            process = subprocess.Popen(
                [sys.executable, "-c", script],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                self.fail("anchored JSON reader blocked on a FIFO")

            self.assertEqual(process.returncode, 0, stderr)
            self.assertIn("regular file", stdout)

    def test_require_missing_private_json_publish_never_overwrites_racing_target(self):
        with TemporaryDirectory() as tmp:
            private = Path(tmp).resolve() / "pilot" / "private"
            private.mkdir(parents=True)
            os.chmod(private, 0o700)
            marker = private / "finalization.json"
            racing_value = {"sentinel": "must-survive"}
            real_stat = os.stat
            observations = []

            def racing_stat(target, *, dir_fd=None, follow_symlinks=True):
                if (
                    dir_fd is not None
                    and os.fspath(target) == "finalization.json"
                    and follow_symlinks is False
                ):
                    observations.append(True)
                    try:
                        return real_stat(
                            target,
                            dir_fd=dir_fd,
                            follow_symlinks=follow_symlinks,
                        )
                    except FileNotFoundError:
                        if len(observations) == 2:
                            descriptor = os.open(
                                target,
                                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                0o600,
                                dir_fd=dir_fd,
                            )
                            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                                json.dump(racing_value, handle)
                        raise
                if dir_fd is None:
                    return real_stat(target, follow_symlinks=follow_symlinks)
                return real_stat(
                    target,
                    dir_fd=dir_fd,
                    follow_symlinks=follow_symlinks,
                )

            with patch.object(os, "stat", side_effect=racing_stat), self.assertRaises(
                FileExistsError
            ):
                write_private_json_anchored(
                    marker,
                    {"finalized": True},
                    require_missing=True,
                )

            self.assertGreaterEqual(len(observations), 2)
            self.assertEqual(json.loads(marker.read_text(encoding="utf-8")), racing_value)

    def test_private_json_writer_is_owner_only_atomic_and_rejects_static_links(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            private = root / "pilot" / "private" / "exercises"
            path = private / "failure.json"

            write_private_json_anchored(path, {"passed": True})

            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")), {"passed": True}
            )
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            self.assertEqual(private.stat().st_mode & 0o077, 0)
            self.assertFalse(
                any(item.name.endswith(".tmp") for item in private.iterdir())
            )

            target = root / "outside.json"
            target.write_text("sentinel", encoding="utf-8")
            path.unlink()
            path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                write_private_json_anchored(path, {"passed": False})
            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

            path.unlink()
            path.mkdir()
            with self.assertRaisesRegex(ValueError, "regular file"):
                write_private_json_anchored(path, {"passed": False})

    def test_private_json_writer_rejects_parent_path_swap_without_redirecting(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            private = root / "pilot" / "private"
            private.mkdir(parents=True)
            os.chmod(private, 0o700)
            anchored = root / "anchored-private"
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.json"
            sentinel.write_text("sentinel", encoding="utf-8")
            real_open = os.open
            swapped = []

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                name = os.fspath(path)
                if not swapped and name.endswith(".tmp"):
                    private.rename(anchored)
                    private.symlink_to(outside, target_is_directory=True)
                    swapped.append(True)
                if dir_fd is None:
                    return real_open(path, flags, mode)
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with patch.object(os, "open", side_effect=racing_open), self.assertRaisesRegex(
                ValueError,
                "declared private path",
            ):
                write_private_json_anchored(
                    private / "decision.json", {"decision": "continue"}
                )

            self.assertEqual(swapped, [True])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(list(outside.glob("*.json")), [sentinel])
            self.assertTrue((anchored / "decision.json").is_file())

    def test_private_json_writer_removes_new_marker_when_parent_swap_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            private = root / "pilot" / "private"
            private.mkdir(parents=True)
            os.chmod(private, 0o700)
            anchored = root / "anchored-private"
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.json"
            sentinel.write_text("sentinel", encoding="utf-8")
            real_open = os.open
            swapped = []

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                name = os.fspath(path)
                if not swapped and name.endswith(".tmp"):
                    private.rename(anchored)
                    private.symlink_to(outside, target_is_directory=True)
                    swapped.append(True)
                if dir_fd is None:
                    return real_open(path, flags, mode)
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with patch.object(os, "open", side_effect=racing_open), self.assertRaisesRegex(
                ValueError,
                "declared private path",
            ):
                write_private_json_anchored(
                    private / "finalization.json",
                    {"finalized": True},
                    require_missing=True,
                )

            self.assertEqual(swapped, [True])
            self.assertFalse((anchored / "finalization.json").exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(list(outside.glob("*.json")), [sentinel])

    def test_private_json_writer_rejects_final_path_swap_before_replace(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            private = root / "pilot" / "private"
            private.mkdir(parents=True)
            os.chmod(private, 0o700)
            path = private / "decision.json"
            path.write_text("{}", encoding="utf-8")
            backup = private / "original-decision.json"
            outside = root / "outside.json"
            outside.write_text("sentinel", encoding="utf-8")
            real_stat = os.stat
            observed = []

            def racing_stat(target, *, dir_fd=None, follow_symlinks=True):
                if (
                    dir_fd is not None
                    and os.fspath(target) == "decision.json"
                    and follow_symlinks is False
                ):
                    observed.append(True)
                    if len(observed) == 2:
                        path.rename(backup)
                        path.symlink_to(outside)
                if dir_fd is None:
                    return real_stat(target, follow_symlinks=follow_symlinks)
                return real_stat(
                    target,
                    dir_fd=dir_fd,
                    follow_symlinks=follow_symlinks,
                )

            with patch.object(os, "stat", side_effect=racing_stat), self.assertRaisesRegex(
                ValueError,
                "changed|symbolic link",
            ):
                write_private_json_anchored(path, {"decision": "continue"})

            self.assertEqual(len(observed), 2)
            self.assertEqual(outside.read_text(encoding="utf-8"), "sentinel")
            self.assertTrue(path.is_symlink())
            self.assertFalse(
                any(item.name.endswith(".tmp") for item in private.iterdir())
            )

    def test_write_pack_is_atomic_idempotent_and_replaces_with_exact_allowlist(self):
        pack = _valid_pack()
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            stale = output / "runs" / "999.json"
            stale.parent.mkdir(parents=True)
            stale.write_text("{}", encoding="utf-8")
            keep = output / "notes.txt"
            keep.write_text("keep", encoding="utf-8")
            hidden = output / ".private-note"
            hidden.write_text("hidden", encoding="utf-8")
            nested = output / "archive" / "notes.txt"
            nested.parent.mkdir()
            nested.write_text("nested", encoding="utf-8")

            first = write_evidence_pack(output, pack)
            second = write_evidence_pack(output, pack)

            self.assertEqual(first["file_count"], second["file_count"])
            self.assertFalse(stale.exists())
            self.assertFalse(keep.exists())
            self.assertFalse(hidden.exists())
            self.assertFalse(nested.exists())
            self.assertFalse((output / "archive").exists())
            self.assertFalse(
                any(path.name.endswith(".tmp") for path in output.rglob("*"))
            )
            self.assertEqual(
                json.loads((output / "runs" / "001.json").read_text(encoding="utf-8")),
                pack["runs"][0],
            )

    def test_write_pack_second_file_failure_leaves_missing_target_absent(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            real_write = __import__(
                "skill2workflow._controlled_lark_pilot_evidence_writer",
                fromlist=["_write_json_atomic"],
            )._write_json_atomic
            calls = []

            def fail_second(parent_fd, name, value):
                calls.append(name)
                if len(calls) == 2:
                    raise OSError("second staged file failed")
                return real_write(parent_fd, name, value)

            with patch(
                "skill2workflow._controlled_lark_pilot_evidence_writer._write_json_atomic",
                side_effect=fail_second,
            ), self.assertRaisesRegex(OSError, "second staged file failed"):
                write_evidence_pack(output, _valid_pack())

            self.assertGreaterEqual(len(calls), 2)
            self.assertFalse(output.exists())

    def test_write_pack_second_file_failure_restores_existing_complete_pack(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            write_evidence_pack(output, _valid_pack())
            notes = output / "notes.txt"
            notes.write_text("pre-call private note", encoding="utf-8")
            hidden = output / ".sentinel"
            hidden.write_text("pre-call hidden note", encoding="utf-8")
            nested = output / "archive" / "notes.txt"
            nested.parent.mkdir()
            nested.write_text("pre-call nested note", encoding="utf-8")
            before = {
                str(path.relative_to(output)): path.read_bytes()
                for path in sorted(output.rglob("*"))
                if path.is_file()
            }
            replacement = deepcopy(_valid_pack())
            replacement["charter"]["expires_on"] = "2026-08-16"
            real_write = __import__(
                "skill2workflow._controlled_lark_pilot_evidence_writer",
                fromlist=["_write_json_atomic"],
            )._write_json_atomic
            calls = []

            def fail_second(parent_fd, name, value):
                calls.append(name)
                if len(calls) == 2:
                    raise OSError("second staged file failed")
                return real_write(parent_fd, name, value)

            with patch(
                "skill2workflow._controlled_lark_pilot_evidence_writer._write_json_atomic",
                side_effect=fail_second,
            ), self.assertRaisesRegex(OSError, "second staged file failed"):
                write_evidence_pack(output, replacement)

            after = {
                str(path.relative_to(output)): path.read_bytes()
                for path in sorted(output.rglob("*"))
                if path.is_file()
            }
            self.assertGreaterEqual(len(calls), 2)
            self.assertEqual(after, before)

    def test_write_pack_omits_optional_none_and_removes_old_optional_json(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            write_evidence_pack(output, _valid_pack())
            pack = _valid_pack()
            pack["exercises"] = {
                "rejection": None,
                "failure": None,
                "rollback": None,
            }
            pack["runs"] = []
            pack["verification"] = None
            pack["decision"] = None
            pack["index"].update(
                build_acceptance_summary(
                    pack["charter"],
                    pack["runs"],
                    0,
                    pack["exercises"],
                    pack["verification"],
                    pack["decision"],
                )
            )

            result = write_evidence_pack(output, pack)

            self.assertEqual(result["file_count"], 2 + len(pack["runs"]))
            self.assertFalse((output / "verification.json").exists())
            self.assertFalse((output / "decision.json").exists())
            self.assertEqual(list((output / "exercises").glob("*.json")), [])

    def test_write_pack_fails_if_declared_output_is_swapped_after_anchoring(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            output.mkdir()
            anchored = root / "anchored-evidence"
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.json"
            sentinel.write_text("sentinel", encoding="utf-8")
            real_open = os.open
            swapped = []

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                name = os.fspath(path)
                if not swapped and name.endswith(".tmp"):
                    output.rename(anchored)
                    output.symlink_to(outside, target_is_directory=True)
                    swapped.append(True)
                if dir_fd is None:
                    return real_open(path, flags, mode)
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with patch.object(os, "open", side_effect=racing_open), self.assertRaisesRegex(
                ValueError,
                "declared output|symbolic link",
            ):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(swapped, [True])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(list(outside.glob("*.json")), [sentinel])
            self.assertEqual(list(anchored.iterdir()), [])

    def test_write_pack_fails_if_declared_output_becomes_missing_or_different(self):
        for replacement in ("missing", "different-directory"):
            with self.subTest(replacement=replacement), TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                output = root / "evidence"
                output.mkdir()
                anchored = root / "anchored-evidence"
                real_open = os.open
                swapped = []

                def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                    name = os.fspath(path)
                    if not swapped and name.endswith(".tmp"):
                        output.rename(anchored)
                        if replacement == "different-directory":
                            output.mkdir()
                        swapped.append(True)
                    if dir_fd is None:
                        return real_open(path, flags, mode)
                    return real_open(path, flags, mode, dir_fd=dir_fd)

                with patch.object(
                    os,
                    "open",
                    side_effect=racing_open,
                ), self.assertRaisesRegex(ValueError, "declared output"):
                    write_evidence_pack(output, _valid_pack())

                self.assertEqual(swapped, [True])
                self.assertEqual(list(anchored.iterdir()), [])
                if output.exists():
                    self.assertEqual(list(output.iterdir()), [])

    def test_write_pack_parent_swap_after_publish_restores_anchored_old_pack(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            declared_parent = root / "declared"
            output = declared_parent / "evidence"
            write_evidence_pack(output, _valid_pack())
            before = {
                str(path.relative_to(output)): path.read_bytes()
                for path in sorted(output.rglob("*"))
                if path.is_file()
            }
            replacement = deepcopy(_valid_pack())
            replacement["charter"]["expires_on"] = "2026-08-16"
            anchored_parent = root / "anchored-declared"
            real_replace = os.replace
            swapped = []

            def swap_parent_after_directory_publish(
                source,
                target,
                *,
                src_dir_fd=None,
                dst_dir_fd=None,
            ):
                result = real_replace(
                    source,
                    target,
                    src_dir_fd=src_dir_fd,
                    dst_dir_fd=dst_dir_fd,
                )
                if source == "stage" and target == "evidence" and not swapped:
                    declared_parent.rename(anchored_parent)
                    declared_parent.mkdir()
                    swapped.append(True)
                return result

            with patch.object(
                os,
                "replace",
                side_effect=swap_parent_after_directory_publish,
            ), self.assertRaisesRegex(RuntimeError, "rollback"):
                write_evidence_pack(output, replacement)

            restored_output = anchored_parent / "evidence"
            after = {
                str(path.relative_to(restored_output)): path.read_bytes()
                for path in sorted(restored_output.rglob("*"))
                if path.is_file()
            }
            self.assertEqual(swapped, [True])
            self.assertEqual(after, before)
            self.assertEqual(list(declared_parent.iterdir()), [])
            self.assertEqual(
                [path for path in anchored_parent.iterdir() if path.name.endswith(".txn")],
                [],
            )

    def test_write_pack_removes_crash_leftover_from_exact_new_pack(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            output.mkdir()
            leftover = output / ".pilot-charter.json.tmp"
            leftover.write_text("crash-leftover", encoding="utf-8")

            result = write_evidence_pack(output, _valid_pack())

            self.assertEqual(result["status"], "written")
            self.assertFalse(leftover.exists())
            self.assertTrue((output / "pilot-charter.json").is_file())

    def test_write_pack_cleans_random_temp_when_atomic_replace_fails(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"

            with patch(
                "skill2workflow._controlled_lark_pilot_evidence_writer.os.replace",
                side_effect=OSError("replace failed"),
            ), self.assertRaisesRegex(OSError, "replace failed"):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(
                [path for path in output.rglob("*") if path.name.endswith(".tmp")],
                [],
            )

    def test_write_pack_fails_closed_without_secure_directory_fd_support(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"

            with patch(
                "skill2workflow._controlled_lark_pilot_evidence_writer._DIR_FD_SUPPORTED",
                False,
            ), self.assertRaisesRegex(ValueError, "directory-fd"):
                write_evidence_pack(output, _valid_pack())

            self.assertFalse(output.exists())

    def test_write_pack_rejects_stale_json_symlink_without_touching_target(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            output.mkdir()
            target = root / "outside.json"
            target.write_text("sentinel", encoding="utf-8")
            (output / "stale.json").symlink_to(target)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

    def test_write_pack_rejects_root_and_symlink_components_without_touching_target(self):
        with self.assertRaisesRegex(ValueError, "root"):
            write_evidence_pack(Path("/"), _valid_pack())

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / "target"
            target.mkdir()
            sentinel = target / "stale.json"
            sentinel.write_text("sentinel", encoding="utf-8")
            linked = root / "linked"
            linked.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                write_evidence_pack(linked, _valid_pack())

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            output.mkdir()
            target = root / "target"
            target.mkdir()
            sentinel = target / "sentinel.txt"
            sentinel.write_text("sentinel", encoding="utf-8")
            (output / "runs").symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(list(target.glob("*.json")), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
