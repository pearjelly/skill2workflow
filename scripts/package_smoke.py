#!/usr/bin/env python3
"""Build a wheel and verify it without importing from the source checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import venv
import zipfile
from email.parser import Parser
from pathlib import Path
from pathlib import PurePosixPath
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List


DEFAULT_WORK_DIR = Path("/tmp/skill2workflow-package-smoke")
MATURITY_CLASSIFIER = "Development Status :: 4 - Beta"
APACHE_2_0_LICENSE_SHA256 = (
    "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
)
REQUIRED_CONSOLE_COMMANDS = (
    "validate",
    "publish",
    "promote",
    "workflow-diff",
    "workflow-artifacts",
    "audit-consistency",
    "run-published",
    "quickstart",
    "service-init",
    "service-token-rotate",
    "service-doctor",
    "systemd-unit",
    "service",
    "schedule-run-due",
    "backup",
    "backup-verify",
    "restore",
    "state-upgrade",
    "state-retention-apply",
    "audit-verify",
    "cancel-run",
    "service-resume",
    "service-cancel",
    "service-show",
    "service-runs",
    "service-recurring-schedules",
    "service-recurring-dispatches",
    "service-workflow-artifacts",
    "service-backup-readiness",
    "service-audit-integrity",
    "service-runtime-info",
    "service-workflow-diff",
    "service-workflow-publish",
    "service-workflow-promote",
    "service-trigger",
    "service-schedule-enable",
    "service-schedule-disable",
    "service-support-bundle",
    "service-audit-consistency",
    "control-snapshot",
)


def run_package_smoke(repo_root: Path, work_dir: Path = DEFAULT_WORK_DIR, reset: bool = True) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    build_venv_dir = work_dir / "build-venv"
    venv_dir = work_dir / "venv"
    wheel_dir = work_dir / "wheelhouse"
    isolated_dir = work_dir / "isolated"
    isolated_fixture = isolated_dir / "approval-flow.workflow.json"
    venv.EnvBuilder(with_pip=True, clear=True).create(build_venv_dir)
    venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    isolated_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        repo_root / "examples" / "workflows" / "approval-flow.workflow.json",
        isolated_fixture,
    )

    build_python = _venv_executable(build_venv_dir, "python")
    python_bin = _venv_executable(venv_dir, "python")
    console_script = _venv_executable(venv_dir, "skill2workflow")

    tooling = _run(
        [
            str(build_python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools>=77.0.1",
        ],
        cwd=isolated_dir,
    )
    build = _run(
        [
            str(build_python),
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
            str(repo_root),
        ],
        cwd=isolated_dir,
    )
    wheel = _built_wheel(wheel_dir)
    wheel_contents = _inspect_wheel(wheel)
    install = _run(
        [
            str(python_bin),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-index",
            str(wheel),
        ],
        cwd=isolated_dir,
    )
    installed_metadata = json.loads(
        _run(
            [
                str(python_bin),
                "-c",
                (
                    "import importlib.metadata as metadata, json; "
                    "distribution=metadata.metadata('skill2workflow'); "
                    "print(json.dumps({'version': metadata.version('skill2workflow'), "
                    "'classifiers': distribution.get_all('Classifier') or []}))"
                ),
            ],
            cwd=isolated_dir,
        )
    )
    version = str(installed_metadata.get("version", ""))
    classifiers = installed_metadata.get("classifiers", [])
    if not isinstance(classifiers, list) or MATURITY_CLASSIFIER not in classifiers:
        raise RuntimeError(
            f"installed wheel metadata must include {MATURITY_CLASSIFIER}"
        )
    help_output = _run([str(console_script), "--help"], cwd=isolated_dir)
    if "usage:" not in help_output:
        raise RuntimeError("installed skill2workflow --help did not print usage text")
    for command in REQUIRED_CONSOLE_COMMANDS:
        command_help = _run(
            [str(console_script), command, "--help"], cwd=isolated_dir
        )
        if "usage:" not in command_help:
            raise RuntimeError(
                f"installed skill2workflow {command} --help did not print usage text"
            )
    bootstrap_root = isolated_dir / "service-bootstrap"
    bootstrap_output = _run(
        [
            str(console_script),
            "service-init",
            "--root",
            str(bootstrap_root),
            "--port",
            "0",
        ],
        cwd=isolated_dir,
    )
    bootstrap_result = json.loads(bootstrap_output)
    bootstrap_config = Path(str(bootstrap_result.get("config_file", ""))).resolve()
    bootstrap_secret_path = Path(
        str(bootstrap_result.get("token_file", ""))
    ).resolve()
    bootstrap_root = bootstrap_root.resolve()
    if (
        bootstrap_result.get("status") != "initialized"
        or bootstrap_root not in bootstrap_config.parents
        or bootstrap_root not in bootstrap_secret_path.parents
        or not bootstrap_config.is_file()
        or not bootstrap_secret_path.is_file()
    ):
        raise RuntimeError("installed service-init did not create its declared workspace")
    bootstrap_secret = bootstrap_secret_path.read_text(encoding="utf-8").strip()
    if (
        len(bootstrap_secret.encode("utf-8")) < 32
        or bootstrap_secret in bootstrap_output
    ):
        raise RuntimeError("installed service-init did not preserve secret redaction")
    rotate_output = _run(
        [
            str(console_script),
            "service-token-rotate",
            "--config",
            str(bootstrap_config),
        ],
        cwd=isolated_dir,
    )
    rotate_result = json.loads(rotate_output)
    rotated_secret = bootstrap_secret_path.read_text(encoding="utf-8").strip()
    if (
        rotate_result.get("status") != "rotated"
        or rotated_secret == bootstrap_secret
        or len(rotated_secret.encode("utf-8")) < 32
        or rotated_secret in rotate_output
    ):
        raise RuntimeError("installed service-token-rotate did not preserve secret redaction")
    bootstrap_secret = rotated_secret
    doctor_output = _run(
        [
            str(console_script),
            "service-doctor",
            "--config",
            str(bootstrap_config),
        ],
        cwd=isolated_dir,
    )
    doctor_result = json.loads(doctor_output)
    doctor_checks = doctor_result.get("checks", [])
    if (
        doctor_result.get("status") != "ready"
        or [check.get("id") for check in doctor_checks]
        != ["config", "auth", "credentials", "state", "bind"]
        or not all(check.get("status") == "passed" for check in doctor_checks)
        or bootstrap_secret in doctor_output
    ):
        raise RuntimeError("installed service-doctor did not validate its generated workspace")
    systemd_unit_status = _qualify_systemd_unit(
        console_script,
        isolated_dir,
        bootstrap_config,
        console_script,
    )
    live_snapshot_status = _qualify_live_snapshot(
        console_script,
        isolated_dir,
        bootstrap_secret_path,
    )
    validate_output = _run(
        [
            str(console_script),
            "validate",
            str(isolated_fixture),
            "--format",
            "json",
        ],
        cwd=isolated_dir,
    )
    validate_result = json.loads(validate_output)
    if not validate_result.get("valid"):
        raise RuntimeError(f"installed skill2workflow validate returned invalid result: {validate_output}")
    _run(
        [
            str(python_bin),
            "-c",
            (
                "import pathlib, skill2workflow, sys; "
                "from skill2workflow.backup import create_state_backup; "
                "from skill2workflow.retention import inspect_state_retention; "
                "from skill2workflow.quickstart import initialize_quickstart_workspace; "
                "from skill2workflow.live_snapshot import fetch_live_control_snapshot; "
                "from skill2workflow.service import RuntimeService; "
                "from skill2workflow.service_bootstrap import initialize_service_workspace; "
                "from skill2workflow.service_doctor import diagnose_service; "
                "source=pathlib.Path(sys.argv[1]).resolve(); "
                "installed=pathlib.Path(skill2workflow.__file__).resolve(); "
                "assert installed != source and source not in installed.parents"
            ),
            str(repo_root),
        ],
        cwd=isolated_dir,
    )

    return {
        "ok": True,
        "work_dir": str(work_dir),
        "venv": str(venv_dir),
        "python": str(python_bin),
        "console_script": str(console_script),
        "wheel": str(wheel),
        "package": "skill2workflow",
        "version": version,
        "maturity_classifier": MATURITY_CLASSIFIER,
        "install_mode": "wheel",
        "isolated_from_source": True,
        "required_console_commands": list(REQUIRED_CONSOLE_COMMANDS),
        "service_bootstrap_status": True,
        "service_token_rotation_status": True,
        "service_doctor_status": True,
        "systemd_unit_status": systemd_unit_status,
        "live_snapshot_status": live_snapshot_status,
        **wheel_contents,
        "tooling_command": tooling.splitlines()[-1] if tooling.splitlines() else "",
        "build_command": build.splitlines()[-1] if build.splitlines() else "",
        "install_command": install.splitlines()[-1] if install.splitlines() else "",
        "help_contains_usage": True,
        "required_command_help_contains_usage": True,
        "validate_status": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="package_smoke", description="Build and verify an isolated wheel locally.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing package smoke work directory contents.")
    args = parser.parse_args(argv)

    result = run_package_smoke(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _run(command: List[str], cwd: Path) -> str:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=environment,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed: {command}\nexit: {code}\nstdout:\n{stdout}\nstderr:\n{stderr}".format(
                command=" ".join(command),
                code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )
    return completed.stdout


def _qualify_live_snapshot(
    console_script: Path,
    isolated_dir: Path,
    token_file: Path,
) -> bool:
    """Run the installed CLI against one strict loopback snapshot response."""

    payload = {
        "schema_version": "skill2workflow-control-snapshot-0.1.0",
        "summary": {
            "workflow_count": 0,
            "run_count": 0,
            "audit_event_count": 0,
            "connector_count": 0,
            "status_counts": {},
            "run_status_counts": {},
        },
        "workflows": [],
        "runs": [],
        "audit_events": [],
        "connectors": [],
        "version_comparisons": [],
        "operator_insights": {},
        "window": {
            "max_items": 100,
            "workflows": {"total": 0, "returned": 0, "truncated": False},
            "runs": {"total": 0, "returned": 0, "truncated": False},
            "audit_events": {"total": 0, "returned": 0, "truncated": False},
            "connectors": {"total": 0, "returned": 0, "truncated": False},
            "version_comparisons": {
                "total": 0,
                "returned": 0,
                "truncated": False,
            },
        },
    }
    expected_token = token_file.read_text(encoding="utf-8").strip()
    observed = {}

    class SnapshotHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            observed["path"] = self.path
            observed["authorization"] = self.headers.get("Authorization", "")
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), SnapshotHandler)
    server.timeout = 2
    thread = threading.Thread(target=server.handle_request, daemon=True)
    output = isolated_dir / "installed-live-snapshot.json"
    thread.start()
    try:
        cli_output = _run(
            [
                str(console_script),
                "control-snapshot",
                "--service-url",
                f"http://127.0.0.1:{server.server_port}",
                "--auth-token-file",
                str(token_file),
                "--output",
                str(output),
            ],
            cwd=isolated_dir,
        )
    finally:
        thread.join(timeout=3)
        server.server_close()
    if thread.is_alive():
        raise RuntimeError("installed live snapshot request did not complete")
    if (
        cli_output
        or observed.get("path") != "/api/v1/control-snapshot"
        or observed.get("authorization") != f"Bearer {expected_token}"
        or json.loads(output.read_text(encoding="utf-8")) != payload
        or output.stat().st_mode & 0o777 != 0o600
    ):
        raise RuntimeError("installed live snapshot client did not preserve its contract")
    return True


def _qualify_systemd_unit(
    console_script: Path,
    isolated_dir: Path,
    config_file: Path,
    executable: Path,
) -> bool:
    """Prove the installed CLI can generate one redacted fixed-port unit."""

    config = json.loads(config_file.read_text(encoding="utf-8"))
    config["service"]["port"] = 8080
    systemd_config = isolated_dir / "systemd-service.json"
    systemd_config.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    systemd_config.chmod(0o600)
    output = isolated_dir / "skill2workflow-wheel.service"
    result = json.loads(
        _run(
            [
                str(console_script),
                "systemd-unit",
                "--config",
                str(systemd_config),
                "--output",
                str(output),
                "--service-user",
                "skill2workflow",
                "--service-group",
                "skill2workflow",
                "--executable",
                str(executable),
            ],
            cwd=isolated_dir,
        )
    )
    content = output.read_text(encoding="utf-8")
    token_value = Path(config["auth"]["token_file"]).read_text(encoding="utf-8").strip()
    if (
        result.get("status") != "written"
        or result.get("unit_name") != output.name
        or output.stat().st_mode & 0o777 != 0o644
        or token_value in content
        or "Environment=" in content
        or "StandardOutput=journal" not in content
        or "ProtectSystem=strict" not in content
        or "ReadWritePaths=" + config["runtime"]["state_dir"] not in content
    ):
        raise RuntimeError("installed systemd unit generator did not preserve its contract")
    return True


def _venv_executable(venv_dir: Path, name: str) -> Path:
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return venv_dir / scripts_dir / f"{name}{suffix}"


def _built_wheel(wheel_dir: Path) -> Path:
    wheels = sorted(wheel_dir.glob("skill2workflow-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"package build must produce exactly one skill2workflow wheel, found {len(wheels)}"
        )
    return wheels[0]


def _inspect_wheel(wheel: Path) -> Dict[str, object]:
    try:
        with zipfile.ZipFile(wheel) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            paths = [PurePosixPath(name) for name in names]
            if any(
                path.is_absolute()
                or not path.parts
                or any(part in ("", ".", "..") for part in path.parts)
                for path in paths
            ):
                raise RuntimeError("wheel contains an unsafe member path")

            dist_info = sorted(
                {
                    path.parts[0]
                    for path in paths
                    if path.parts[0].endswith(".dist-info")
                }
            )
            if len(dist_info) != 1:
                raise RuntimeError("wheel must contain exactly one dist-info directory")
            allowed_roots = {"skill2workflow", dist_info[0]}
            unexpected_roots = sorted(
                {path.parts[0] for path in paths} - allowed_roots
            )
            if unexpected_roots:
                raise RuntimeError(
                    "wheel contains unexpected top-level content: "
                    + ", ".join(unexpected_roots)
                )

            forbidden_parts = {"__pycache__", "pilot-evidence", "private", "secrets"}
            forbidden_suffixes = {
                ".db",
                ".env",
                ".jsonl",
                ".key",
                ".pem",
                ".pyc",
                ".sqlite",
                ".sqlite3",
                ".token",
            }
            forbidden = sorted(
                path.as_posix()
                for path in paths
                if forbidden_parts.intersection(path.parts)
                or path.suffix.lower() in forbidden_suffixes
            )
            if forbidden:
                raise RuntimeError("wheel contains private or state artifacts")

            license_name = f"{dist_info[0]}/licenses/LICENSE"
            if license_name not in names:
                raise RuntimeError("wheel license file is missing")
            license_bytes = archive.read(license_name)
            license_text = license_bytes.decode("utf-8")
            if (
                hashlib.sha256(license_bytes).hexdigest()
                != APACHE_2_0_LICENSE_SHA256
                or "Apache License" not in license_text
                or "Version 2.0" not in license_text
            ):
                raise RuntimeError("wheel license file is invalid")

            metadata_name = f"{dist_info[0]}/METADATA"
            if metadata_name not in names:
                raise RuntimeError("wheel metadata is missing")
            metadata = Parser().parsestr(
                archive.read(metadata_name).decode("utf-8")
            )
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise RuntimeError("wheel contents could not be inspected") from error

    version = metadata.get("Version", "")
    expected_dist_info = f"skill2workflow-{version}.dist-info"
    expected_project_urls = {
        "Homepage, https://github.com/pearjelly/skill2workflow",
        "Documentation, https://github.com/pearjelly/skill2workflow/tree/main/docs",
        "Repository, https://github.com/pearjelly/skill2workflow",
        "Issues, https://github.com/pearjelly/skill2workflow/issues",
        "Changelog, https://github.com/pearjelly/skill2workflow/blob/main/CHANGELOG.md",
        "Security, https://github.com/pearjelly/skill2workflow/blob/main/SECURITY.md",
    }
    expected_python_classifiers = {
        f"Programming Language :: Python :: {python_version}"
        for python_version in ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14")
    }
    project_urls = set(metadata.get_all("Project-URL") or [])
    classifiers = set(metadata.get_all("Classifier") or [])
    if (
        metadata.get("Name") != "skill2workflow"
        or not version
        or dist_info[0] != expected_dist_info
        or metadata.get("License-Expression") != "Apache-2.0"
        or metadata.get_all("License-File") != ["LICENSE"]
        or metadata.get("Requires-Python") != ">=3.9"
        or project_urls != expected_project_urls
        or not expected_python_classifiers.issubset(classifiers)
    ):
        raise RuntimeError("wheel metadata does not match the package contract")
    return {
        "wheel_file_count": len(names),
        "license_included": True,
        "private_artifacts_excluded": True,
        "wheel_metadata_valid": True,
        "project_urls_valid": True,
        "python_classifiers_valid": True,
    }


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("package smoke work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("package smoke work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
