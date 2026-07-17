import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.controlled_lark_pilot_evidence import (
    build_acceptance_summary,
    write_evidence_pack,
)
from skill2workflow._controlled_lark_pilot_evidence_writer import (
    write_private_json_anchored,
)

from tests.test_controlled_lark_pilot_evidence import _valid_pack


class ControlledLarkPilotEvidenceWriterTests(TestCase):
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

    def test_write_pack_is_atomic_idempotent_and_removes_only_stale_json(self):
        pack = _valid_pack()
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            stale = output / "runs" / "999.json"
            stale.parent.mkdir(parents=True)
            stale.write_text("{}", encoding="utf-8")
            keep = output / "notes.txt"
            keep.write_text("keep", encoding="utf-8")

            first = write_evidence_pack(output, pack)
            second = write_evidence_pack(output, pack)

            self.assertEqual(first["file_count"], second["file_count"])
            self.assertFalse(stale.exists())
            self.assertEqual(keep.read_text(encoding="utf-8"), "keep")
            self.assertFalse(
                any(path.name.endswith(".tmp") for path in output.rglob("*"))
            )
            self.assertEqual(
                json.loads((output / "runs" / "001.json").read_text(encoding="utf-8")),
                pack["runs"][0],
            )

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
                "declared output",
            ):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(swapped, [True])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(list(outside.glob("*.json")), [sentinel])
            self.assertTrue((anchored / "evidence-index.json").is_file())

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
                self.assertTrue((anchored / "evidence-index.json").is_file())
                if output.exists():
                    self.assertEqual(list(output.iterdir()), [])

    def test_write_pack_random_temp_does_not_block_on_crash_leftover(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            output.mkdir()
            leftover = output / ".pilot-charter.json.tmp"
            leftover.write_text("crash-leftover", encoding="utf-8")

            result = write_evidence_pack(output, _valid_pack())

            self.assertEqual(result["status"], "written")
            self.assertEqual(leftover.read_text(encoding="utf-8"), "crash-leftover")
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
