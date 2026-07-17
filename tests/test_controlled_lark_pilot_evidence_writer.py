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

from tests.test_controlled_lark_pilot_evidence import _valid_pack


class ControlledLarkPilotEvidenceWriterTests(TestCase):
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
