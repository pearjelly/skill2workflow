import json
import os
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts.package_smoke import (
    PACKAGED_UI_DATA_FILES,
    REQUIRED_CONSOLE_COMMANDS,
    _inspect_wheel,
    _run,
    run_package_smoke,
)


class PackageSmokeTests(TestCase):
    def test_smoke_builds_and_installs_a_wheel_without_editable_source(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            work = root / "work"
            fixture = repo / "examples" / "workflows" / "approval-flow.workflow.json"
            fixture.parent.mkdir(parents=True)
            fixture.write_text("{}", encoding="utf-8")
            skill_fixture = repo / "examples" / "skills" / "approval-flow" / "SKILL.md"
            skill_fixture.parent.mkdir(parents=True)
            skill_fixture.write_text("## Checklist\n\n1. Review draft\n", encoding="utf-8")
            commands = []

            class FakeEnvBuilder:
                def __init__(self, **_kwargs):
                    pass

                def create(self, target):
                    binary_dir = Path(target) / ("Scripts" if os.name == "nt" else "bin")
                    binary_dir.mkdir(parents=True)
                    (binary_dir / ("python.exe" if os.name == "nt" else "python")).touch()
                    (binary_dir / ("skill2workflow.exe" if os.name == "nt" else "skill2workflow")).touch()

            def fake_run(command, cwd):
                command = [str(value) for value in command]
                commands.append((command, Path(cwd)))
                if "wheel" in command:
                    wheel_dir = Path(command[command.index("--wheel-dir") + 1])
                    wheel_dir.mkdir(parents=True, exist_ok=True)
                    wheel = wheel_dir / "skill2workflow-0.1.0-py3-none-any.whl"
                    with zipfile.ZipFile(wheel, "w") as archive:
                        archive.writestr("skill2workflow/__init__.py", "")
                        archive.writestr(
                            "skill2workflow-0.1.0.dist-info/licenses/LICENSE",
                            (
                                Path(__file__).resolve().parents[1] / "LICENSE"
                            ).read_text(encoding="utf-8"),
                        )
                        archive.writestr(
                            "skill2workflow-0.1.0.dist-info/METADATA",
                            _valid_metadata(),
                        )
                        data_prefix = "skill2workflow-0.1.0.data"
                        for name in PACKAGED_UI_DATA_FILES:
                            archive.writestr(f"{data_prefix}/{name}", "{}")
                if "importlib.metadata" in " ".join(command):
                    return (
                        '{"version": "0.1.0", "classifiers": '
                        '["Development Status :: 4 - Beta"]}\n'
                    )
                if command[-1:] == ["--help"]:
                    return "usage: skill2workflow\n" + "\n".join(
                        REQUIRED_CONSOLE_COMMANDS
                    )
                if command[-1:] == ["--version"]:
                    return "skill2workflow 0.1.0\n"
                if "service-init" in command:
                    bootstrap_root = Path(command[command.index("--root") + 1])
                    secret_path = bootstrap_root / "secrets" / "ingress-token"
                    config_path = bootstrap_root / "config" / "service.json"
                    state_path = bootstrap_root / "state"
                    credential_path = bootstrap_root / "secrets" / "connectors"
                    secret_path.parent.mkdir(parents=True)
                    config_path.parent.mkdir(parents=True)
                    state_path.mkdir(parents=True)
                    credential_path.mkdir(parents=True)
                    secret_path.write_text("s" * 48 + "\n", encoding="utf-8")
                    config_path.write_text(
                        json.dumps(
                            {
                                "schema_version": "skill2workflow-service-0.2.0",
                                "service": {"host": "127.0.0.1", "port": 0},
                                "runtime": {
                                    "state_dir": str(state_path),
                                    "storage": "sqlite",
                                },
                                "auth": {
                                    "provider": "bearer_token_file",
                                    "token_file": str(secret_path),
                                },
                                "credentials": {
                                    "provider": "directory",
                                    "directory": str(credential_path),
                                },
                            }
                        ),
                        encoding="utf-8",
                    )
                    return json.dumps(
                        {
                            "status": "initialized",
                            "config_file": str(config_path),
                            "token_file": str(secret_path),
                            "state_dir": str(state_path),
                            "credential_directory": str(credential_path),
                        }
                    )
                if "service-doctor" in command:
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-service-doctor-result-0.1.0",
                            "status": "ready",
                            "checks": [
                                {"id": check_id, "status": "passed", "code": "ready"}
                                for check_id in (
                                    "config",
                                    "auth",
                                    "credentials",
                                    "state",
                                    "bind",
                                )
                            ],
                        }
                    )
                if "service-token-rotate" in command and "--help" not in command:
                    config_path = Path(command[command.index("--config") + 1])
                    config = json.loads(config_path.read_text(encoding="utf-8"))
                    secret_path = Path(config["auth"]["token_file"])
                    secret_path.write_text("r" * 48 + "\n", encoding="utf-8")
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-service-token-rotation-result-0.1.0",
                            "status": "rotated",
                            "token_file": str(secret_path),
                        }
                    )
                if "systemd-unit" in command:
                    output_path = Path(command[command.index("--output") + 1])
                    config_path = Path(command[command.index("--config") + 1])
                    config = json.loads(config_path.read_text(encoding="utf-8"))
                    output_path.write_text(
                        "StandardOutput=journal\nProtectSystem=strict\n"
                        f"ReadWritePaths={config['runtime']['state_dir']}\n",
                        encoding="utf-8",
                    )
                    return json.dumps(
                        {"status": "written", "unit_name": output_path.name}
                    )
                if "authoring-export" in command:
                    output_dir = Path(command[command.index("--output-dir") + 1])
                    output_dir.mkdir()
                    for filename in (
                        "workflow.json",
                        "workflow.litegraph.json",
                        "compile-review.json",
                        "manifest.json",
                    ):
                        (output_dir / filename).write_text("{}", encoding="utf-8")
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-authoring-artifacts-result-0.1.0",
                            "status": "created",
                            "valid": True,
                            "files": [
                                "workflow.json",
                                "workflow.litegraph.json",
                                "compile-review.json",
                                "manifest.json",
                            ],
                        }
                    )
                if "authoring-verify" in command:
                    return json.dumps(
                        {
                            "schema_version": (
                                "skill2workflow-authoring-artifacts-verification-0.1.0"
                            ),
                            "valid": True,
                            "files": 4,
                            "errors": [],
                        }
                    )
                if "compile" in command:
                    output_path = Path(command[command.index("--output") + 1])
                    output_path.write_text("{}", encoding="utf-8")
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-skill-compile-review-0.1.0",
                            "ordered_step_count": 1,
                            "executable_node_count": 1,
                            "human_gate_count": 0,
                            "verification_node_count": 0,
                            "hard_gate_count": 0,
                            "notices": [
                                "human_gate_not_inferred",
                                "verification_not_inferred",
                            ],
                        }
                    )
                if "validate" in command:
                    return '{"valid": true}\n'
                if "bundle-create" in command:
                    output_path = Path(command[command.index("--output") + 1])
                    output_path.write_bytes(b"bundle")
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-workflow-bundle-verification-0.1.0",
                            "status": "created",
                            "valid": True,
                        }
                    )
                if "bundle-verify" in command:
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-workflow-bundle-verification-0.1.0",
                            "valid": True,
                            "errors": [],
                        }
                    )
                if "bundle-publish" in command:
                    return json.dumps(
                        {
                            "workflow_id": "workflow_demo",
                            "version": "0.1.0",
                            "status": "published",
                        }
                    )
                if "bundle-diff" in command:
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-workflow-bundle-diff-0.1.0",
                            "workflow_id": "workflow_demo",
                            "changed": False,
                            "changes": {"sections": []},
                        }
                    )
                if "bundle-preflight" in command:
                    return json.dumps(
                        {
                            "schema_version": "skill2workflow-workflow-preflight-0.1.0",
                            "ready": True,
                            "safety": {"side_effect_free": True},
                        }
                    )
                if "bundle-run" in command:
                    if "--summary" in command:
                        return json.dumps(
                            {
                                "schema_version": "skill2workflow-workflow-bundle-summary-0.1.0",
                                "run_id": "run_bundle_summary",
                                "workflow_id": "workflow_demo",
                                "workflow_version": "0.1.0",
                                "status": "waiting",
                                "current_node": "approval",
                                "event_count": 3,
                                "node_result_count": 1,
                                "bundle_run": {
                                    "bundle_verified": True,
                                    "side_effects_authorized": False,
                                    "bundle_sha256": "a" * 64,
                                },
                            }
                        )
                    return json.dumps(
                        {
                            "run_id": "run_bundle",
                            "workflow_id": "workflow_demo",
                            "status": "waiting",
                        }
                    )
                return "ok\n"

            with patch("scripts.package_smoke.venv.EnvBuilder", FakeEnvBuilder), patch(
                "scripts.package_smoke._run", side_effect=fake_run
            ), patch(
                "scripts.package_smoke._qualify_live_snapshot",
                return_value=True,
            ) as qualify_live_snapshot, patch(
                "scripts.package_smoke._qualify_installed_ui",
                return_value=True,
            ) as qualify_installed_ui:
                result = run_package_smoke(repo, work)

        flattened = [part for command, _cwd in commands for part in command]
        self.assertNotIn("-e", flattened)
        self.assertIn("wheel", flattened)
        self.assertEqual(result["install_mode"], "wheel")
        self.assertTrue(result["isolated_from_source"])
        self.assertTrue(result["version_matches_metadata"])
        self.assertTrue(result["service_bootstrap_status"])
        self.assertTrue(result["service_token_rotation_status"])
        self.assertTrue(result["service_doctor_status"])
        self.assertTrue(result["systemd_unit_status"])
        self.assertTrue(result["live_snapshot_status"])
        self.assertTrue(result["release_manifest_status"])
        self.assertTrue(result["release_sbom_status"])
        self.assertEqual(
            result["release_sbom_file_count"], result["release_manifest_file_count"]
        )
        self.assertEqual(
            result["release_sbom_wheel_sha256"], result["release_artifact_sha256"]
        )
        systemd_commands = [
            command
            for command, _cwd in commands
            if "systemd-unit" in command and "--output" in command
        ]
        self.assertEqual(len(systemd_commands), 1)
        executable_index = systemd_commands[0].index("--executable") + 1
        self.assertTrue(systemd_commands[0][executable_index].endswith("skill2workflow"))
        qualify_live_snapshot.assert_called_once()
        qualify_installed_ui.assert_called_once()
        self.assertTrue(result["ui_status"])
        self.assertTrue(result["license_included"])
        self.assertTrue(result["private_artifacts_excluded"])
        self.assertTrue(result["bundle_status"])
        self.assertTrue(result["bundle_publish_status"])
        self.assertTrue(result["bundle_diff_status"])
        self.assertTrue(result["bundle_preflight_status"])
        self.assertTrue(result["bundle_run_status"])
        self.assertTrue(result["bundle_summary_status"])
        self.assertTrue(result["compile_review_status"])
        self.assertTrue(result["authoring_artifact_status"])
        self.assertTrue(result["wheel_metadata_valid"])
        self.assertTrue(result["project_urls_valid"])
        self.assertTrue(result["python_classifiers_valid"])
        self.assertEqual(
            result["maturity_classifier"], "Development Status :: 4 - Beta"
        )
        self.assertEqual(
            result["required_console_commands"], list(REQUIRED_CONSOLE_COMMANDS)
        )
        runtime_cwds = [cwd for command, cwd in commands if "skill2workflow" in Path(command[0]).name]
        self.assertTrue(runtime_cwds)
        self.assertTrue(
            all(cwd == (work / "isolated").resolve() for cwd in runtime_cwds)
        )

    def test_run_removes_pythonpath_and_disables_user_site_packages(self):
        with patch.dict(os.environ, {"PYTHONPATH": "/source/leak"}, clear=False), patch(
            "scripts.package_smoke.subprocess.run"
        ) as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "ok"
            run.return_value.stderr = ""

            _run(["python", "-V"], Path("/tmp"))

        environment = run.call_args.kwargs["env"]
        self.assertNotIn("PYTHONPATH", environment)
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")

    def test_wheel_inspection_rejects_private_or_state_artifacts(self):
        with TemporaryDirectory() as temporary:
            wheel = Path(temporary) / "skill2workflow-0.1.0-py3-none-any.whl"
            _write_test_wheel(
                wheel,
                extra={"docs/pilot-evidence/loop-40/run.json": "{}"},
            )

            with self.assertRaisesRegex(RuntimeError, "unexpected top-level"):
                _inspect_wheel(wheel)

    def test_wheel_inspection_requires_license_and_matching_metadata(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing_license = root / "missing-license.whl"
            _write_test_wheel(missing_license, include_license=False)
            bad_metadata = root / "bad-metadata.whl"
            _write_test_wheel(
                bad_metadata,
                metadata=(
                    "Metadata-Version: 2.4\n"
                    "Name: skill2workflow\n"
                    "Version: 0.1.0\n"
                    "License-Expression: Proprietary\n"
                    "Requires-Python: >=3.10\n"
                ),
            )

            with self.assertRaisesRegex(RuntimeError, "license"):
                _inspect_wheel(missing_license)
            with self.assertRaisesRegex(RuntimeError, "metadata"):
                _inspect_wheel(bad_metadata)

    def test_wheel_inspection_rejects_modified_license_text(self):
        with TemporaryDirectory() as temporary:
            wheel = Path(temporary) / "modified-license.whl"
            official = (
                Path(__file__).resolve().parents[1] / "LICENSE"
            ).read_text(encoding="utf-8")
            _write_test_wheel(
                wheel,
                license_text=official + "\nmodified\n",
            )

            with self.assertRaisesRegex(RuntimeError, "license"):
                _inspect_wheel(wheel)


def _write_test_wheel(
    path: Path,
    *,
    include_license: bool = True,
    license_text: str = "",
    metadata: str = "",
    extra=None,
) -> None:
    metadata = metadata or _valid_metadata()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("skill2workflow/__init__.py", "")
        archive.writestr(
            "skill2workflow-0.1.0.dist-info/METADATA", metadata
        )
        if include_license:
            archive.writestr(
                "skill2workflow-0.1.0.dist-info/licenses/LICENSE",
                license_text
                or (Path(__file__).resolve().parents[1] / "LICENSE").read_text(
                    encoding="utf-8"
                ),
            )
        for name, value in (extra or {}).items():
            archive.writestr(name, value)


def _valid_metadata() -> str:
    classifiers = "".join(
        f"Classifier: Programming Language :: Python :: {version}\n"
        for version in ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14")
    )
    return (
        "Metadata-Version: 2.4\n"
        "Name: skill2workflow\n"
        "Version: 0.1.0\n"
        "License-Expression: Apache-2.0\n"
        "License-File: LICENSE\n"
        "Requires-Python: >=3.9\n"
        "Project-URL: Homepage, https://github.com/pearjelly/skill2workflow\n"
        "Project-URL: Repository, https://github.com/pearjelly/skill2workflow\n"
        "Project-URL: Issues, https://github.com/pearjelly/skill2workflow/issues\n"
        "Project-URL: Documentation, https://github.com/pearjelly/skill2workflow/tree/main/docs\n"
        "Project-URL: Changelog, https://github.com/pearjelly/skill2workflow/blob/main/CHANGELOG.md\n"
        "Project-URL: Security, https://github.com/pearjelly/skill2workflow/blob/main/SECURITY.md\n"
        + classifiers
    )
