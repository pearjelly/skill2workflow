import json
import os
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts.reproducible_build import (
    DEFAULT_SOURCE_DATE_EPOCH,
    REPRODUCIBLE_BUILD_SCHEMA_VERSION,
    _validate_epoch,
    run_reproducible_build,
    write_reproducible_evidence,
)


class ReproducibleBuildTests(TestCase):
    def test_fixed_epoch_builds_are_compared_and_evidence_is_public(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            work = root / "work"
            repo.mkdir()

            class FakeEnvBuilder:
                def __init__(self, **_kwargs):
                    pass

                def create(self, target):
                    binary_dir = Path(target) / ("Scripts" if os.name == "nt" else "bin")
                    binary_dir.mkdir(parents=True)
                    (binary_dir / ("python.exe" if os.name == "nt" else "python")).touch()

            commands = []

            def fake_run(command, *, cwd, extra_environment=None):
                command = [str(value) for value in command]
                commands.append((command, Path(cwd), extra_environment or {}))
                if "wheel" in command:
                    wheel_dir = Path(command[command.index("--wheel-dir") + 1])
                    wheel_dir.mkdir(parents=True, exist_ok=True)
                    _write_wheel(wheel_dir / "skill2workflow-0.1.0-py3-none-any.whl")
                return "ok\n"

            with patch("scripts.reproducible_build.venv.EnvBuilder", FakeEnvBuilder), patch(
                "scripts.reproducible_build._run", side_effect=fake_run
            ):
                result = run_reproducible_build(repo, work)

            self.assertTrue(result["ok"])
            self.assertTrue(result["builds_equal"])
            self.assertEqual(result["builds_compared"], 2)
            self.assertEqual(result["source_date_epoch"], DEFAULT_SOURCE_DATE_EPOCH)
            evidence_path = Path(result["evidence_file"])
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["schema_version"], REPRODUCIBLE_BUILD_SCHEMA_VERSION)
            self.assertEqual(evidence["artifact"]["sha256"], result["artifact_sha256"])
            self.assertEqual(evidence["environment"]["timezone"], "UTC")
            self.assertEqual(evidence_path.stat().st_mode & 0o777, 0o644)
            self.assertEqual(list(evidence_path.parent.glob("*.tmp")), [])
            wheel_commands = [entry for entry in commands if "wheel" in entry[0]]
            self.assertEqual(len(wheel_commands), 2)
            for _command, _cwd, environment in wheel_commands:
                self.assertEqual(environment["SOURCE_DATE_EPOCH"], str(DEFAULT_SOURCE_DATE_EPOCH))
                self.assertEqual(environment["PYTHONHASHSEED"], "0")

    def test_evidence_writer_is_atomic_and_public(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "nested" / "reproducible-build.json"
            evidence = {"schema_version": REPRODUCIBLE_BUILD_SCHEMA_VERSION, "builds_equal": True}

            write_reproducible_evidence(output, evidence)

            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), evidence)
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)
            self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_epoch_validation_is_fail_closed(self):
        for value in (-1, True, "946684800"):
            with self.assertRaises(ValueError):
                _validate_epoch(value)


def _write_wheel(path: Path) -> None:
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: skill2workflow\n"
        "Version: 0.1.0\n"
        "Requires-Python: >=3.9\n"
        "License-Expression: Apache-2.0\n"
    )
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in (
            ("skill2workflow/__init__.py", "__version__ = '0.1.0'\n"),
            ("skill2workflow-0.1.0.dist-info/METADATA", metadata),
        ):
            info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, content)
