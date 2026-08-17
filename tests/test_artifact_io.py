import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.artifact_io import (
    MAX_WORKFLOW_ARTIFACT_BYTES,
    encode_workflow_artifact,
    read_workflow_artifact,
)


class WorkflowArtifactIoTests(TestCase):
    def test_encode_rejects_oversized_artifact_before_installation(self):
        with self.assertRaisesRegex(
            ValueError,
            f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes",
        ):
            encode_workflow_artifact({"description": "x" * MAX_WORKFLOW_ARTIFACT_BYTES})

    def test_read_rejects_oversized_artifact_before_opening(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.json"
            path.write_bytes(b" " * (MAX_WORKFLOW_ARTIFACT_BYTES + 1))

            with patch("skill2workflow.artifact_io.os.open") as open_file:
                with self.assertRaisesRegex(
                    ValueError,
                    f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes",
                ):
                    read_workflow_artifact(path)
            open_file.assert_not_called()

    def test_read_rejects_symlink_and_path_replacement(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "artifact.json"
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            path.symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                read_workflow_artifact(path)

            path.unlink()
            path.write_text("{}", encoding="utf-8")
            replacement = root / "replacement.json"
            replacement.write_text("{}", encoding="utf-8")
            real_open = os.open
            replaced = False

            def replace_before_open(open_path, flags, *args, **kwargs):
                nonlocal replaced
                if Path(open_path) == path and not replaced:
                    replaced = True
                    replacement.replace(path)
                return real_open(open_path, flags, *args, **kwargs)

            with patch(
                "skill2workflow.artifact_io.os.open",
                side_effect=replace_before_open,
            ):
                with self.assertRaisesRegex(
                    ValueError, "workflow artifact changed while being read"
                ):
                    read_workflow_artifact(path)
    def test_read_rejects_growth_past_bound(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.json"
            path.write_text("{}", encoding="utf-8")
            with patch(
                "skill2workflow.artifact_io.os.read",
                return_value=b"x" * (MAX_WORKFLOW_ARTIFACT_BYTES + 1),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes",
                ):
                    read_workflow_artifact(path)
