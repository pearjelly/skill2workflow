#!/usr/bin/env python3
"""Exercise portable systemd-unit generation through the real CLI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK_DIR = Path("/tmp/skill2workflow-systemd-service-loop56")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument(
        "--systemd-analyze-verify",
        action="store_true",
        help="also run systemd-analyze verify against the generated unit",
    )
    args = parser.parse_args(argv)

    work_dir = args.work_dir.resolve()
    _prepare_work_dir(work_dir, reset=not args.no_reset)
    port = _available_port()
    workspace = work_dir / "workspace"
    executable = _write_wrapper(work_dir / "bin" / "skill2workflow")
    initialized = _run_cli(
        "service-init",
        "--root",
        str(workspace),
        "--port",
        str(port),
    )
    config_file = Path(initialized["config_file"])
    token = Path(initialized["token_file"]).read_text(encoding="utf-8").strip()
    unit_file = work_dir / "skill2workflow-team-a.service"
    service_user = "root" if args.systemd_analyze_verify else "skill2workflow"
    generated = _run_cli(
        "systemd-unit",
        "--config",
        str(config_file),
        "--output",
        str(unit_file),
        "--service-user",
        service_user,
        "--service-group",
        service_user,
        "--executable",
        str(executable),
    )
    unit = unit_file.read_text(encoding="utf-8")
    doctor = _run_cli("service-doctor", "--config", str(config_file))
    duplicate = _run_cli_process(
        "systemd-unit",
        "--config",
        str(config_file),
        "--output",
        str(unit_file),
        "--service-user",
        service_user,
        "--executable",
        str(executable),
    )

    systemd_verification = None
    if args.systemd_analyze_verify:
        systemd_verification = _verify_systemd_unit(unit_file)

    checks = {
        "cli_wrote_expected_unit": (
            generated.get("status") == "written"
            and generated.get("unit_name") == unit_file.name
            and generated.get("unit_file") == str(unit_file)
        ),
        "doctor_accepts_same_workspace": doctor.get("status") == "ready",
        "owner_can_read_nonsecret_unit": stat.S_IMODE(unit_file.stat().st_mode) == 0o644,
        "least_privilege_paths": (
            f"ReadWritePaths={initialized['state_dir']}" in unit
            and f"ReadOnlyPaths={initialized['config_file']}" in unit
            and str(initialized["token_file"]) in unit
            and str(initialized["credential_directory"]) in unit
        ),
        "hardening_directives_present": all(
            directive in unit
            for directive in (
                "UMask=0077",
                "StandardOutput=journal",
                "StandardError=journal",
                "NoNewPrivileges=yes",
                "ProtectSystem=strict",
                "ProtectHome=read-only",
                "PrivateTmp=yes",
                "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6",
                "SendSIGKILL=no",
            )
        ),
        "no_secret_or_environment_value": token not in unit and "Environment=" not in unit,
        "existing_unit_is_not_overwritten": duplicate.returncode == 1
        and "must not already exist" in duplicate.stderr
        and token not in duplicate.stderr,
    }
    if systemd_verification is not None:
        checks["systemd_analyze_verify"] = systemd_verification["status"] == "passed"
    evidence = {
        "schema_version": "skill2workflow-systemd-service-evidence-0.1.0",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
    }
    if systemd_verification is not None:
        evidence["systemd_analyze_verify"] = systemd_verification
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _write_wrapper(path: Path) -> Path:
    path.parent.mkdir(mode=0o700)
    path.write_text(
        "#!/bin/sh\nexec \"{}\" -m skill2workflow.cli \"$@\"\n".format(
            sys.executable
        ),
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path.resolve()


def _run_cli(*arguments):
    process = _run_cli_process(*arguments)
    if process.returncode != 0 or process.stderr:
        raise RuntimeError("skill2workflow CLI command failed")
    return json.loads(process.stdout)


def _run_cli_process(*arguments):
    environment = dict(os.environ)
    source = str(REPO_ROOT / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = source if not existing else source + os.pathsep + existing
    return subprocess.run(
        [sys.executable, "-m", "skill2workflow.cli", *arguments],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _verify_systemd_unit(unit_file: Path):
    analyzer = shutil.which("systemd-analyze")
    if not analyzer:
        return {"status": "failed", "code": "systemd_analyze_missing"}
    try:
        process = subprocess.run(
            [analyzer, "verify", str(unit_file)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "failed", "code": "systemd_analyze_unavailable"}
    return {
        "status": "passed" if process.returncode == 0 else "failed",
        "code": "verified" if process.returncode == 0 else "systemd_analyze_rejected",
    }


def _available_port() -> int:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])
    finally:
        listener.close()


def _prepare_work_dir(work_dir: Path, *, reset: bool) -> None:
    if work_dir == Path(work_dir.anchor) or work_dir == REPO_ROOT or REPO_ROOT in work_dir.parents:
        raise ValueError("systemd service work directory must be outside the repository")
    if work_dir.exists():
        if not reset:
            raise ValueError("systemd service work directory already exists")
        shutil.rmtree(work_dir)
    work_dir.mkdir(mode=0o700, parents=True)


if __name__ == "__main__":
    raise SystemExit(main())
