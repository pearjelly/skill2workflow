#!/usr/bin/env python3
"""Build a wheel and verify it without importing from the source checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import venv
import zipfile
from email.parser import Parser
from pathlib import Path
from pathlib import PurePosixPath
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List

try:
    from release_manifest import (
        PACKAGED_UI_DATA_FILES,
        build_release_manifest,
        write_release_manifest,
    )
    from release_sbom import build_release_sbom, write_release_sbom
except ImportError:  # pragma: no cover - exercised when imported as scripts.package_smoke
    from scripts.release_manifest import (
        PACKAGED_UI_DATA_FILES,
        build_release_manifest,
        write_release_manifest,
    )
    from scripts.release_sbom import build_release_sbom, write_release_sbom


DEFAULT_WORK_DIR = Path("/tmp/skill2workflow-package-smoke")
MATURITY_CLASSIFIER = "Development Status :: 4 - Beta"
APACHE_2_0_LICENSE_SHA256 = (
    "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
)
REQUIRED_CONSOLE_COMMANDS = (
    "validate",
    "authoring-export",
    "authoring-verify",
    "authoring-repair",
    "authoring-bundle",
    "authoring-publish",
    "authoring-service-release-preflight",
    "authoring-service-release-target-review",
    "authoring-service-publish",
    "bundle-create",
    "bundle-verify",
    "bundle-publish",
    "bundle-diff",
    "bundle-preflight",
    "bundle-run",
    "run",
    "resume",
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
    "service-go-live-check",
    "service-lark-tenant-credential-check",
    "systemd-unit",
    "service",
    "schedule-run-due",
    "backup",
    "backup-verify",
    "backup-list",
    "backup-retention-plan",
    "workflows",
    "schedules",
    "schedule-dispatches",
    "schedule-dispatch-review",
    "schedule-dispatch-review-get",
    "restore",
    "state-upgrade",
    "state-retention-apply",
    "audit-verify",
    "audit-evidence",
    "audit-evidence-verify",
    "cancel-run",
    "service-resume",
    "service-cancel",
    "service-show",
    "service-runs",
    "service-run-page",
    "service-recurring-schedules",
    "service-recurring-schedule-add",
    "service-recurring-schedule-update",
    "service-recurring-schedule-patch",
    "service-recurring-schedule-delete",
    "service-recurring-dispatches",
    "service-recurring-dispatch-page",
    "service-recurring-dispatch-review",
    "service-recurring-dispatch-review-get",
    "ui",
    "service-workflow-artifacts",
    "service-backup-readiness",
    "service-backup-inventory",
    "service-backup-inventory-page",
    "service-backup-retention-plan",
    "service-retention-readiness",
    "service-operational-readiness",
    "service-probe",
    "service-wait",
    "service-audit-integrity",
    "service-runtime-info",
    "service-workflows",
    "service-workflow-diff",
    "service-workflow-explain",
    "preflight",
    "service-workflow-preflight",
    "service-workflow-release-preflight",
    "service-workflow-release-target-review",
    "service-workflow-publish",
    "service-workflow-promote",
    "service-workflow-deprecate",
    "service-trigger",
    "service-schedule-enable",
    "service-schedule-disable",
    "service-support-bundle",
    "service-audit-consistency",
    "service-audit-events",
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
    isolated_skill = isolated_dir / "approval-flow.SKILL.md"
    compiled_skill_workflow = isolated_dir / "compiled-approval-flow.workflow.json"
    authoring_artifact_dir = isolated_dir / "authoring-artifacts"
    authoring_repair_backup_dir = isolated_dir / "authoring-artifacts-before-repair"
    authoring_bundle_path = isolated_dir / "authoring-artifacts.s2w"
    authoring_publish_state_dir = isolated_dir / "authoring-publish-control"
    venv.EnvBuilder(with_pip=True, clear=True).create(build_venv_dir)
    venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    isolated_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        repo_root / "examples" / "workflows" / "approval-flow.workflow.json",
        isolated_fixture,
    )
    shutil.copy2(
        repo_root / "examples" / "skills" / "approval-flow" / "SKILL.md",
        isolated_skill,
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
    _verify_packaged_ui_assets(wheel)
    release_manifest = build_release_manifest(wheel)
    release_manifest_path = work_dir / "release-artifact-manifest.json"
    write_release_manifest(release_manifest_path, release_manifest)
    release_sbom = build_release_sbom(wheel)
    release_sbom_path = work_dir / "release-artifact-sbom.json"
    write_release_sbom(release_sbom_path, release_sbom)
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
    version_output = _run([str(console_script), "--version"], cwd=isolated_dir).strip()
    if version_output != f"skill2workflow {version}":
        raise RuntimeError(
            "installed skill2workflow --version did not match wheel metadata"
        )
    for command in REQUIRED_CONSOLE_COMMANDS:
        command_help = _run(
            [str(console_script), command, "--help"], cwd=isolated_dir
        )
        if "usage:" not in command_help:
            raise RuntimeError(
                f"installed skill2workflow {command} --help did not print usage text"
            )
    go_live_help = _run(
        [str(console_script), "service-go-live-check", "--help"],
        cwd=isolated_dir,
    )
    if "--verify-lark-tenant-credential" not in go_live_help:
        raise RuntimeError(
            "installed service-go-live-check is missing the Feishu credential preflight option"
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
    ui_status = _qualify_installed_ui(console_script, isolated_dir)
    _qualify_installed_skill_compiles(console_script, isolated_dir)
    _qualify_installed_skill_compile_recovery(repo_root, console_script, isolated_dir)
    _qualify_installed_skill_versions(repo_root, console_script, isolated_dir)
    _qualify_installed_preflight_inputs(repo_root, console_script, isolated_dir)
    _qualify_installed_http_assertions(repo_root, console_script, isolated_dir)
    _qualify_installed_skill_http_actions(repo_root, console_script, isolated_dir)
    _qualify_installed_quickstart_inputs(python_bin, console_script, isolated_dir)
    _qualify_installed_draft_input_ui(repo_root, console_script, isolated_dir)
    _qualify_installed_ui_static(repo_root, console_script, isolated_dir)
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
    compile_review = json.loads(
        _run(
            [
                str(console_script),
                "compile",
                str(isolated_skill),
                "--output",
                str(compiled_skill_workflow),
                "--review",
            ],
            cwd=isolated_dir,
        )
    )
    compiled_skill_validation = json.loads(
        _run(
            [
                str(console_script),
                "validate",
                str(compiled_skill_workflow),
                "--format",
                "json",
            ],
            cwd=isolated_dir,
        )
    )
    if not isinstance(compile_review, dict) or not isinstance(
        compiled_skill_validation, dict
    ):
        raise RuntimeError("installed skill2workflow compile review did not return objects")
    if (
        compile_review.get("schema_version")
        != "skill2workflow-skill-compile-review-0.1.0"
        or set(compile_review)
        != {
            "schema_version",
            "ordered_step_count",
            "executable_node_count",
            "human_gate_count",
            "verification_node_count",
            "hard_gate_count",
            "notices",
        }
        or not all(
            isinstance(compile_review.get(field), int)
            and not isinstance(compile_review.get(field), bool)
            and 0 <= compile_review[field] <= 10000
            for field in (
                "ordered_step_count",
                "executable_node_count",
                "human_gate_count",
                "verification_node_count",
                "hard_gate_count",
            )
        )
        or not isinstance(compile_review.get("notices"), list)
        or len(compile_review["notices"]) > 3
        or not all(isinstance(notice, str) for notice in compile_review["notices"])
        or any(
            notice
            not in {
                "checklist_not_found",
                "human_gate_not_inferred",
                "verification_not_inferred",
            }
            for notice in compile_review["notices"]
        )
        or len(set(compile_review["notices"])) != len(compile_review["notices"])
        or not compiled_skill_workflow.is_file()
        or not compiled_skill_validation.get("valid")
    ):
        raise RuntimeError("installed skill2workflow compile review did not preserve its contract")
    authoring_artifacts = json.loads(
        _run(
            [
                str(console_script),
                "authoring-export",
                str(isolated_skill),
                "--output-dir",
                str(authoring_artifact_dir),
            ],
            cwd=isolated_dir,
        )
    )
    authoring_workflow_validation = json.loads(
        _run(
            [
                str(console_script),
                "validate",
                str(authoring_artifact_dir / "workflow.json"),
                "--format",
                "json",
            ],
            cwd=isolated_dir,
        )
    )
    authoring_artifact_verification = json.loads(
        _run(
            [str(console_script), "authoring-verify", str(authoring_artifact_dir)],
            cwd=isolated_dir,
        )
    )
    authoring_repair_preflight_result = json.loads(
        _run(
            [
                str(console_script),
                "authoring-repair",
                str(isolated_skill),
                str(authoring_artifact_dir),
                "--backup-dir",
                str(authoring_repair_backup_dir),
                "--dry-run",
            ],
            cwd=isolated_dir,
        )
    )
    authoring_repair_preflight_backup_exists = authoring_repair_backup_dir.exists()
    (authoring_artifact_dir / "workflow.json").write_text("{}", encoding="utf-8")
    authoring_repair_result = json.loads(
        _run(
            [
                str(console_script),
                "authoring-repair",
                str(isolated_skill),
                str(authoring_artifact_dir),
                "--backup-dir",
                str(authoring_repair_backup_dir),
            ],
            cwd=isolated_dir,
        )
    )
    authoring_repaired_verification = json.loads(
        _run(
            [str(console_script), "authoring-verify", str(authoring_artifact_dir)],
            cwd=isolated_dir,
        )
    )
    authoring_publish_result = json.loads(
        _run(
            [
                str(console_script),
                "authoring-publish",
                str(authoring_artifact_dir),
                "--state-dir",
                str(authoring_publish_state_dir),
                "--storage",
                "sqlite",
            ],
            cwd=isolated_dir,
        )
    )
    authoring_bundle_result = json.loads(
        _run(
            [
                str(console_script),
                "authoring-bundle",
                str(authoring_artifact_dir),
                "--output",
                str(authoring_bundle_path),
            ],
            cwd=isolated_dir,
        )
    )
    authoring_bundle_verification = json.loads(
        _run(
            [str(console_script), "bundle-verify", str(authoring_bundle_path)],
            cwd=isolated_dir,
        )
    )
    if (
        not isinstance(authoring_artifacts, dict)
        or authoring_artifacts.get("schema_version")
        != "skill2workflow-authoring-artifacts-result-0.1.0"
        or authoring_artifacts.get("status") != "created"
        or authoring_artifacts.get("valid") is not True
        or authoring_artifacts.get("files")
        != [
            "workflow.json",
            "workflow.litegraph.json",
            "compile-review.json",
            "manifest.json",
        ]
        or not all(
            (authoring_artifact_dir / name).is_file()
            for name in authoring_artifacts["files"]
        )
        or (authoring_artifact_dir / "SKILL.md").exists()
        or not isinstance(authoring_workflow_validation, dict)
        or not authoring_workflow_validation.get("valid")
        or not isinstance(authoring_artifact_verification, dict)
        or authoring_artifact_verification.get("schema_version")
        != "skill2workflow-authoring-artifacts-verification-0.1.0"
        or authoring_artifact_verification.get("valid") is not True
        or authoring_artifact_verification.get("files") != 4
        or authoring_artifact_verification.get("errors") != []
        or not isinstance(authoring_repair_preflight_result, dict)
        or authoring_repair_preflight_result.get("schema_version")
        != "skill2workflow-authoring-artifacts-repair-preflight-0.1.0"
        or authoring_repair_preflight_result.get("status") != "ready"
        or authoring_repair_preflight_result.get("valid") is not True
        or authoring_repair_preflight_result.get("previous_valid") is not True
        or authoring_repair_preflight_backup_exists
        or not isinstance(authoring_repair_result, dict)
        or authoring_repair_result.get("schema_version")
        != "skill2workflow-authoring-artifacts-repair-result-0.1.0"
        or authoring_repair_result.get("status") != "repaired"
        or authoring_repair_result.get("valid") is not True
        or authoring_repair_result.get("previous_valid") is not False
        or not authoring_repair_backup_dir.is_dir()
        or not isinstance(authoring_repaired_verification, dict)
        or authoring_repaired_verification.get("valid") is not True
        or not isinstance(authoring_publish_result, dict)
        or authoring_publish_result.get("status") != "published"
        or not isinstance(authoring_publish_result.get("workflow_id"), str)
        or not authoring_publish_result["workflow_id"]
        or authoring_publish_state_dir.exists() is not True
        or not isinstance(authoring_bundle_result, dict)
        or authoring_bundle_result.get("status") != "created"
        or authoring_bundle_result.get("valid") is not True
        or not authoring_bundle_path.is_file()
        or not isinstance(authoring_bundle_verification, dict)
        or authoring_bundle_verification.get("valid") is not True
        or authoring_bundle_verification.get("errors") != []
    ):
        raise RuntimeError(
            "installed skill2workflow authoring export did not preserve its contract"
        )
    bundle_path = isolated_dir / "approval-flow.s2w"
    bundle_create_result = json.loads(
        _run(
            [
                str(console_script),
                "bundle-create",
                str(isolated_fixture),
                "--output",
                str(bundle_path),
            ],
            cwd=isolated_dir,
        )
    )
    bundle_verify_result = json.loads(
        _run(
            [str(console_script), "bundle-verify", str(bundle_path)],
            cwd=isolated_dir,
        )
    )
    bundle_control_state_dir = isolated_dir / "bundle-control"
    bundle_publish_result = json.loads(
        _run(
            [
                str(console_script),
                "bundle-publish",
                str(bundle_path),
                "--state-dir",
                str(bundle_control_state_dir),
                "--storage",
                "sqlite",
            ],
            cwd=isolated_dir,
        )
    )
    bundle_diff_result = json.loads(
        _run(
            [
                str(console_script),
                "bundle-diff",
                str(bundle_path),
                str(bundle_path),
            ],
            cwd=isolated_dir,
        )
    )
    bundle_preflight_result = json.loads(
        _run(
            [
                str(console_script),
                "bundle-preflight",
                str(bundle_path),
            ],
            cwd=isolated_dir,
        )
    )
    bundle_run_state_dir = isolated_dir / "bundle-run-control"
    bundle_run_result = json.loads(
        _run(
            [
                str(console_script),
                "bundle-run",
                str(bundle_path),
                "--state-dir",
                str(bundle_run_state_dir),
                "--storage",
                "sqlite",
            ],
            cwd=isolated_dir,
        )
    )
    bundle_summary_result = json.loads(
        _run(
            [
                str(console_script),
                "bundle-run",
                str(bundle_path),
                "--summary",
                "--state-dir",
                str(isolated_dir / "bundle-summary-control"),
                "--storage",
                "sqlite",
            ],
            cwd=isolated_dir,
        )
    )
    audit_evidence_path = isolated_dir / "audit-evidence" / "window.json"
    audit_evidence_result = json.loads(
        _run(
            [
                str(console_script),
                "audit-evidence",
                "--state-dir",
                str(bundle_control_state_dir),
                "--output",
                str(audit_evidence_path),
                "--max-items",
                "10",
            ],
            cwd=isolated_dir,
        )
    )
    audit_evidence_verification = json.loads(
        _run(
            [str(console_script), "audit-evidence-verify", str(audit_evidence_path)],
            cwd=isolated_dir,
        )
    )
    if (
        bundle_create_result.get("valid") is not True
        or bundle_create_result.get("status") != "created"
        or bundle_verify_result.get("valid") is not True
        or bundle_publish_result.get("status") != "published"
        or bundle_diff_result.get("changed") is not False
        or bundle_preflight_result.get("ready") is not True
        or bundle_run_result.get("status") != "waiting"
        or bundle_summary_result.get("schema_version")
        != "skill2workflow-workflow-bundle-summary-0.1.0"
        or bundle_summary_result.get("status") != "waiting"
        or bundle_summary_result.get("bundle_run", {}).get("bundle_verified") is not True
        or bundle_summary_result.get("bundle_run", {}).get("side_effects_authorized")
        is not False
        or not _is_sha256(
            bundle_summary_result.get("bundle_run", {}).get("bundle_sha256")
        )
        or not bundle_path.is_file()
        or audit_evidence_result.get("output") != str(audit_evidence_path)
        or not isinstance(audit_evidence_result.get("event_count"), int)
        or audit_evidence_result.get("event_count", 0) <= 0
        or not isinstance(audit_evidence_result.get("truncated"), bool)
        or not _is_sha256(audit_evidence_result.get("head_digest"))
        or not audit_evidence_path.is_file()
        or audit_evidence_verification.get("schema_version")
        != "skill2workflow-audit-evidence-verification-0.1.0"
        or audit_evidence_verification.get("valid") is not True
        or audit_evidence_verification.get("event_count") != audit_evidence_result.get("event_count")
        or audit_evidence_verification.get("truncated") != audit_evidence_result.get("truncated")
        or audit_evidence_verification.get("head_digest") != audit_evidence_result.get("head_digest")
    ):
        raise RuntimeError("installed bundle or audit-evidence commands did not preserve their contract")
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
        "go_live_preflight_option_status": True,
        "systemd_unit_status": systemd_unit_status,
        "live_snapshot_status": live_snapshot_status,
        "ui_status": ui_status,
        "release_manifest_status": True,
        "release_manifest_file_count": len(release_manifest["files"]),
        "release_artifact_sha256": release_manifest["artifact"]["sha256"],
        "release_sbom_status": True,
        "release_sbom_file_count": len(release_sbom["files"]),
        "release_sbom_wheel_sha256": _sbom_wheel_sha256(release_sbom),
        **wheel_contents,
        "tooling_command": tooling.splitlines()[-1] if tooling.splitlines() else "",
        "build_command": build.splitlines()[-1] if build.splitlines() else "",
        "install_command": install.splitlines()[-1] if install.splitlines() else "",
        "help_contains_usage": True,
        "version_matches_metadata": True,
        "required_command_help_contains_usage": True,
        "validate_status": True,
        "compile_review_status": True,
        "authoring_artifact_status": True,
        "authoring_repair_preflight_status": True,
        "authoring_repair_status": True,
        "authoring_bundle_status": True,
        "authoring_publish_status": True,
        "bundle_status": True,
        "bundle_publish_status": True,
        "bundle_diff_status": True,
        "bundle_preflight_status": True,
        "bundle_run_status": True,
        "bundle_summary_status": True,
        "audit_evidence_status": True,
        "audit_evidence_verification_status": True,
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


def _sbom_wheel_sha256(sbom: Dict[str, object]) -> str:
    comment = str(sbom.get("documentComment", ""))
    prefix = "skill2workflow-release-sbom-0.1.0; wheel-sha256="
    if not comment.startswith(prefix):
        raise RuntimeError("release SBOM document comment is malformed")
    return comment[len(prefix) :]


def _is_sha256(value: object) -> bool:
    digest = str(value or "")
    return len(digest) == 64 and all(
        character in "0123456789abcdef" for character in digest
    )


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


def _qualify_installed_preflight_inputs(repo_root: Path, console_script: Path, isolated_dir: Path) -> bool:
    result = json.loads(_run([
        sys.executable, str(repo_root / 'scripts/preflight_input_boundary_smoke.py'),
        '--executable', str(console_script),
    ], cwd=isolated_dir))
    checks = ('exact_ascii', 'exact_unicode', 'oversize_ascii', 'oversize_unicode',
              'numeric_expansion', 'bundle_parity', 'refusal_no_effects', 'valid_trigger')
    if result != {'ok': True, 'installed': True, 'checks': {name: True for name in checks}}:
        raise RuntimeError('installed preflight input qualification failed')
    return True


def _qualify_installed_http_assertions(repo_root: Path, console_script: Path, isolated_dir: Path) -> bool:
    result = json.loads(_run(
        [sys.executable, str(repo_root / "scripts" / "http_assertion_smoke.py"),
         "--executable", str(console_script)], cwd=isolated_dir,
    ))
    if result != {"ok": True, "installed": True, "cases_verified": 2}:
        raise RuntimeError("installed HTTP assertion qualification failed")
    return True


def _qualify_installed_skill_http_actions(repo_root: Path, console_script: Path, isolated_dir: Path) -> bool:
    result = json.loads(_run(
        [sys.executable, str(repo_root / "scripts" / "skill_http_action_smoke.py"),
         "--executable", str(console_script)], cwd=isolated_dir,
    ))
    if result != {"ok": True, "installed": True, "cases_verified": 7}:
        raise RuntimeError("installed Skill HTTP action qualification failed")
    return True


def _qualify_installed_quickstart_inputs(python_bin: Path, console_script: Path, isolated_dir: Path) -> bool:
    code = (
        'import json, os, sys; from pathlib import Path; '
        'from skill2workflow.quickstart_smoke import _qualify_input_quickstart; '
        'print(json.dumps(_qualify_input_quickstart(Path(sys.argv[1]), Path(sys.argv[2]), dict(os.environ))))'
    )
    result = json.loads(_run([str(python_bin), '-c', code, str(console_script), str(isolated_dir)], cwd=isolated_dir))
    expected = {name: True for name in ('custom_input_waiting', 'invalid_input_no_workspace',
                'network_prefix_refused', 'custom_input_approved_http', 'custom_input_compact_result',
                'quickstart_preview_no_workspace', 'required_mapping_no_workspace')}
    if result != expected:
        raise RuntimeError('installed input-aware quickstart qualification failed')
    return True


def _qualify_installed_ui_static(repo_root: Path, console_script: Path, isolated_dir: Path) -> bool:
    result = json.loads(_run([
        sys.executable, str(repo_root / 'scripts/ui_static_smoke.py'),
        '--executable', str(console_script),
    ], cwd=isolated_dir))
    if result != {'ok': True, 'installed': True, 'cases_verified': 10, 'private_file_excluded': True}:
        raise RuntimeError('installed UI static boundary qualification failed')
    return True


def _qualify_installed_draft_input_ui(repo_root: Path, console_script: Path, isolated_dir: Path) -> bool:
    result = json.loads(_run(
        [sys.executable, str(repo_root / 'scripts' / 'draft_input_ui_smoke.py'), '--executable', str(console_script)],
        cwd=isolated_dir,
    ))
    if result != {'ok': True, 'installed': True, 'cases_verified': 13, 'module_served': True, 'diagnostics_verified': 8}:
        raise RuntimeError('installed draft input UI qualification failed')
    return True


def _qualify_installed_skill_compile_recovery(repo_root: Path, console_script: Path, isolated_dir: Path) -> bool:
    result = json.loads(_run(
        [sys.executable, str(repo_root / 'scripts' / 'skill_compile_recovery_smoke.py'), '--executable', str(console_script)],
        cwd=isolated_dir,
    ))
    if result != {'ok': True, 'installed': True, 'cases_verified': 10,
                  'diagnostic_cases_verified': 4, 'legacy_cases_verified': 2,
                  'cli_cases_verified': 2, 'module_served': True} or any(
                      result.get(key) is not True for key in ('ok', 'installed', 'module_served')):
        raise RuntimeError('installed Skill compile recovery qualification failed')
    return True


def _qualify_installed_skill_versions(repo_root: Path, console_script: Path, isolated_dir: Path) -> bool:
    result = json.loads(_run(
        [sys.executable, str(repo_root / 'scripts' / 'skill_version_smoke.py'), '--executable', str(console_script)],
        cwd=isolated_dir,
    ))
    names = {'compile', 'artifacts', 'repair', 'bundles', 'publication',
             'immutable_conflict', 'pinned_runs', 'quickstart', 'ui', 'invalid_source'}
    if (not isinstance(result, dict) or set(result) != {'ok', 'installed', 'checks'}
            or result.get('ok') is not True or result.get('installed') is not True
            or not isinstance(result.get('checks'), dict) or set(result['checks']) != names
            or any(value is not True for value in result['checks'].values())):
        raise RuntimeError('installed versioned Skill qualification failed')
    return True


def _qualify_installed_skill_compiles(console_script: Path, isolated_dir: Path) -> bool:
    """Qualify process headings through only the installed CLI and local UI."""

    for section in ("Workflow", "Steps"):
        fixture_dir = isolated_dir / f"skill-compile-{section.lower()}"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        source = fixture_dir / "SKILL.md"
        markdown = (
            "---\nname: installed-process\ndescription: >-\n"
            "  Compile reviewed input.\n  Keep the intended identity.\n"
            "metadata:\n  name: private-metadata-name-canary\n"
            "  description: private-metadata-description-canary\n---\n\n"
            f"## {section}\n\n"
            "1. Prepare output\n"
            "2. 等待负责人审核 <!-- skill2workflow: human_gate -->\n"
            "3. Verify completion\n"
        )
        source.write_text(markdown, encoding="utf-8")
        compiled = json.loads(
            _run([str(console_script), "compile", str(source), "--review"], cwd=isolated_dir)
        )
        _require_installed_process_compile(compiled, section, str(source), source_offset=12)
        _validate_installed_process_compile(
            console_script, isolated_dir, compiled, fixture_dir / "cli.workflow.json"
        )

        status, compiled = _installed_ui_json_request(
            console_script, isolated_dir, "/api/v1/skill-compiles",
            {"skill_markdown": markdown},
        )
        if status != 200:
            raise RuntimeError("installed UI Skill compile did not accept a process section")
        _require_installed_process_compile(compiled, section, "SKILL.md", source_offset=12)
        _validate_installed_process_compile(
            console_script, isolated_dir, compiled, fixture_dir / "ui.workflow.json"
        )

    status, rejected = _installed_ui_json_request(
        console_script, isolated_dir, "/api/v1/skill-compiles",
        {"skill_markdown": (
            "## Workflow\n\n1. Private ambiguous source step\n\n"
            "## Steps\n\n1. Verify completion\n"
        )},
    )
    if status != 400 or rejected != {"error": "skill compile rejected"}:
        raise RuntimeError("installed UI Skill compile did not reject ambiguity without source text")
    return True


def _require_installed_process_compile(compiled, section: str, source_file: str, *, source_offset: int = 12) -> None:
    expected_review = {
        "schema_version": "skill2workflow-skill-compile-review-0.1.0",
        "ordered_step_count": 3,
        "executable_node_count": 3,
        "human_gate_count": 1,
        "verification_node_count": 1,
        "hard_gate_count": 0,
        "notices": [],
    }
    if not isinstance(compiled, dict) or compiled.get("review") != expected_review:
        raise RuntimeError("installed Skill compile did not preserve process step counts and gates")
    workflow = compiled.get("workflow")
    identity = workflow.get('workflow') if isinstance(workflow, dict) else None
    if not isinstance(identity, dict) or identity.get('id') != 'workflow_installed_process' or identity.get('name') != 'installed-process' or identity.get('description') != 'Compile reviewed input. Keep the intended identity.':
        raise RuntimeError('installed Skill compile did not preserve frontmatter identity and text')
    nodes = workflow.get("nodes") if isinstance(workflow, dict) else None
    if (
        not isinstance(nodes, list)
        or len(nodes) != 6
        or not all(isinstance(node, dict) for node in nodes)
        or [node.get("type") for node in nodes]
        != ["start", "step", "human_gate", "verification", "failure", "end"]
        or [node.get("title") for node in nodes[1:4]]
        != ["Prepare output", "等待负责人审核", "Verify completion"]
    ):
        raise RuntimeError("installed Skill compile did not preserve executable steps and gates")
    for index, node in enumerate(nodes[1:4], 1):
        metadata = node.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("source") != {
            "file": source_file,
            "kind": "ordered_step",
            "index": index,
            "line": index + source_offset,
            "section": section,
        }:
            raise RuntimeError("installed Skill compile did not preserve process source provenance")


def _validate_installed_process_compile(
    console_script: Path, isolated_dir: Path, compiled, output: Path,
) -> None:
    output.write_text(json.dumps(compiled["workflow"]), encoding="utf-8")
    validation = json.loads(
        _run([str(console_script), "validate", str(output), "--format", "json"], cwd=isolated_dir)
    )
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        raise RuntimeError("installed Skill compile did not produce valid Workflow DSL")


def _installed_ui_json_request(
    console_script: Path, isolated_dir: Path, path: str, payload: Dict[str, object],
):
    """Make one JSON request to a credential-free installed UI process."""

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    process = subprocess.Popen(
        [str(console_script), "ui", "--port", str(port), "--once"],
        cwd=str(isolated_dir),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    result = None
    deadline = time.monotonic() + 5
    try:
        while time.monotonic() < deadline:
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}{path}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    response = urllib.request.urlopen(request, timeout=1)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    if response.headers.get("Cache-Control") != "no-store":
                        raise RuntimeError("installed UI JSON response was cacheable")
                    result = response.status, json.loads(response.read().decode("utf-8"))
                break
            except (OSError, urllib.error.URLError):
                if process.poll() is not None:
                    break
                time.sleep(0.05)
        if result is None:
            raise RuntimeError("installed UI JSON request did not complete")
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
    if process.returncode != 0:
        raise RuntimeError("installed UI JSON server did not exit cleanly")
    return result


def _qualify_installed_ui(console_script: Path, isolated_dir: Path) -> bool:
    """Prove an installed wheel serves and locally validates through its UI."""

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    process = subprocess.Popen(
        [str(console_script), "ui", "--port", str(port), "--once"],
        cwd=str(isolated_dir),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    body = b""
    error = None
    deadline = time.monotonic() + 5
    try:
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/web/index.html", timeout=1
                ) as response:
                    body = response.read()
                break
            except (OSError, urllib.error.URLError) as caught:
                error = caught
                time.sleep(0.05)
        if not body:
            raise RuntimeError(f"installed UI did not serve index.html: {error}")
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
    if process.returncode != 0:
        raise RuntimeError("installed UI server did not exit cleanly")
    if b"skill2workflow" not in body or b"Workflow DSL Visual Editor" not in body:
        raise RuntimeError("installed UI served an unexpected index document")
    if b"Validate DSL" not in body:
        raise RuntimeError("installed UI did not serve the Workflow DSL validation action")

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        control_port = probe.getsockname()[1]
    process = subprocess.Popen(
        [str(console_script), "ui", "--port", str(control_port), "--once"],
        cwd=str(isolated_dir),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    control_script = b""
    error = None
    deadline = time.monotonic() + 5
    try:
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{control_port}/web/control.js", timeout=1
                ) as response:
                    control_script = response.read()
                break
            except (OSError, urllib.error.URLError) as caught:
                error = caught
                time.sleep(0.05)
        if not control_script:
            raise RuntimeError(f"installed UI did not serve control.js: {error}")
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
    if process.returncode != 0:
        raise RuntimeError("installed UI control script server did not exit cleanly")
    if (
        b"LIVE_WORKFLOW_RELEASE_URL" not in control_script
        or b"LIVE_WORKFLOW_RELEASE_TARGET_REVIEW_URL" not in control_script
        or b"validateWorkflowReleaseTargetReview" not in control_script
        or b"response.status === 409" not in control_script
        or b"candidate.targetReview = null" not in control_script
        or b"state.liveWorkflowPromotionConflict = true" not in control_script
        or b"state.liveWorkflowDeprecationConflict = true" not in control_script
        or b"state.liveScheduleDispatchReviewConflict = true" not in control_script
        or b"state.liveRunActionConflict = true" not in control_script
    ):
        raise RuntimeError("installed UI did not serve the interactive control script")

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        validation_port = probe.getsockname()[1]
    process = subprocess.Popen(
        [str(console_script), "ui", "--port", str(validation_port), "--once"],
        cwd=str(isolated_dir),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    validation = None
    error = None
    request_body = json.dumps(
        {
            "workflow": json.loads(
                (isolated_dir / "approval-flow.workflow.json").read_text(
                    encoding="utf-8"
                )
            )
        },
        separators=(",", ":"),
    ).encode("utf-8")
    deadline = time.monotonic() + 5
    try:
        while time.monotonic() < deadline:
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{validation_port}/api/v1/workflow-validations",
                    data=request_body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=1) as response:
                    if response.headers.get("Cache-Control") != "no-store":
                        raise RuntimeError("installed UI validation response was cacheable")
                    validation = json.loads(response.read().decode("utf-8"))
                break
            except (OSError, urllib.error.URLError) as caught:
                error = caught
                time.sleep(0.05)
        if validation is None:
            raise RuntimeError(f"installed UI did not validate Workflow DSL: {error}")
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
    if process.returncode != 0:
        raise RuntimeError("installed UI validation server did not exit cleanly")
    if validation != {
        "schema_version": "skill2workflow-local-workflow-validation-0.1.0",
        "valid": True,
        "error_count": 0,
        "errors": [],
        "truncated": False,
    }:
        raise RuntimeError("installed UI did not preserve the Workflow DSL validation contract")
    return True


def _verify_packaged_ui_assets(wheel: Path) -> None:
    """Require the installed artifact to carry the static UI and examples."""

    with zipfile.ZipFile(Path(wheel)) as archive:
        names = set(archive.namelist())
    dist_info = sorted({
        name.split("/", 1)[0]
        for name in names
        if name.split("/", 1)[0].endswith(".dist-info")
    })
    if len(dist_info) != 1:
        raise RuntimeError("wheel must contain exactly one dist-info directory")
    data_root = f"{dist_info[0][:-len('.dist-info')]}.data"
    required = {f"{data_root}/{relative}" for relative in PACKAGED_UI_DATA_FILES}
    if not required.issubset(names):
        raise RuntimeError("wheel is missing packaged UI or example assets")


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
            data_root = f"{dist_info[0][:-len('.dist-info')]}.data"
            allowed_roots = {"skill2workflow", dist_info[0], data_root}
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
