#!/usr/bin/env python3
"""Run the bounded local evidence suite for the self-hosted production baseline."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


EVIDENCE_SCHEMA_VERSION = "skill2workflow-production-baseline-evidence-0.1.0"
WORK_DIR_MARKER = ".skill2workflow-production-baseline"
WORK_DIR_MARKER_VALUE = "skill2workflow production baseline work directory\n"
CHECK_TIMEOUT_SECONDS = 180
SUITE_TIMEOUT_SECONDS = 600


def run_baseline(
    work_dir: Path,
    *,
    command_runner=None,
) -> Dict[str, object]:
    """Run every fixed local production-baseline check and write redacted evidence."""

    work_dir = Path(work_dir).resolve()
    _reset_work_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    work_dir.chmod(0o700)
    (work_dir / WORK_DIR_MARKER).write_text(WORK_DIR_MARKER_VALUE, encoding="utf-8")
    (work_dir / WORK_DIR_MARKER).chmod(0o600)

    runner = command_runner or _run_command
    started = time.monotonic()
    checks: List[Dict[str, object]] = []
    for name, command, child_dir in _suite(work_dir):
        if time.monotonic() - started >= SUITE_TIMEOUT_SECONDS:
            checks.append({"name": name, "status": "skipped", "reason": "suite_timeout"})
            continue
        try:
            result = runner(command, ROOT)
            exit_code, timed_out = _normalize_result(result)
            checks.append(
                {
                    "name": name,
                    "status": "passed" if exit_code == 0 else "failed",
                    "exit_code": exit_code,
                    "timed_out": timed_out,
                }
            )
        except (OSError, RuntimeError, ValueError):
            checks.append(
                {
                    "name": name,
                    "status": "failed",
                    "exit_code": None,
                    "timed_out": False,
                    "reason": "runner_error",
                }
            )
        finally:
            if child_dir is not None:
                _remove_owned_path(child_dir)

    passed = sum(check["status"] == "passed" for check in checks)
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "status": "passed" if len(checks) == len(_suite(work_dir)) and passed == len(checks) else "failed",
        "check_count": len(checks),
        "passed_count": passed,
        "checks": checks,
    }
    _write_evidence(work_dir / "production-baseline-evidence.json", evidence)
    return evidence


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evidence = run_baseline(args.work_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "passed" else 1


def _suite(work_dir: Path):
    python = sys.executable
    source_files = [str(path.relative_to(ROOT)) for path in sorted((SRC / "skill2workflow").glob("*.py"))]

    def script(name: str, *arguments: str, child: Optional[str] = None):
        child_dir = work_dir / child if child is not None else None
        command = [python, f"scripts/{name}.py", *arguments]
        if child_dir is not None:
            command.extend(("--work-dir", str(child_dir)))
        return (name, command, child_dir)

    return [
        ("unit_tests", [python, "-m", "unittest", "discover", "-s", "tests", "-v"], None),
        ("py_compile", [python, "-m", "py_compile", *source_files], None),
        script("package_smoke", child="package"),
        script("reproducible_build", child="reproducible"),
        ("secret_hygiene", [python, "scripts/secret_hygiene.py", "--repository-root", str(ROOT)], None),
        script("security_boundary_smoke", child="security"),
        script("observability_smoke", child="observability"),
        ("observability_rules", [python, "scripts/observability_rules_smoke.py"], None),
        ("observability_dashboard", [python, "scripts/observability_dashboard_smoke.py"], None),
        script("service_boundary_smoke", child="service-boundary"),
        script("service_doctor_smoke", child="service-doctor"),
        script("backup_restore_smoke", child="backup-restore"),
        script("state_upgrade_smoke", child="state-upgrade"),
        script("retention_smoke", child="retention"),
        script("cancellation_smoke", child="cancellation"),
        script("interrupted_recovery_smoke", child="interrupted-recovery"),
        script("schedule_smoke", child="schedule"),
        script("recurring_scheduler_smoke", child="recurring-scheduler"),
        (
            "service_soak_smoke",
            [
                python,
                "scripts/service_soak_smoke.py",
                "--cycles",
                "3",
                "--triggers-per-cycle",
                "6",
                "--work-dir",
                str(work_dir / "service-soak"),
            ],
            work_dir / "service-soak",
        ),
    ]


def _run_command(command: Sequence[str], cwd: Path) -> Tuple[int, bool]:
    environment = dict(os.environ)
    source_path = str(cwd / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = source_path if not existing else f"{source_path}{os.pathsep}{existing}"
    try:
        completed = subprocess.run(
            list(command),
            cwd=str(cwd),
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, True
    return int(completed.returncode), False


def _normalize_result(result) -> Tuple[int, bool]:
    if isinstance(result, tuple) and len(result) == 2:
        return int(result[0]), bool(result[1])
    if isinstance(result, int):
        return result, False
    raise ValueError("command runner returned an unsupported result")


def _reset_work_dir(work_dir: Path) -> None:
    if work_dir in {Path("/"), Path.home()}:
        raise ValueError("production baseline work_dir must not be the filesystem root or home directory")
    if work_dir == ROOT or ROOT in work_dir.parents:
        raise ValueError("production baseline work_dir must be outside the repository")
    if not work_dir.exists():
        return
    if work_dir.is_symlink() or not work_dir.is_dir():
        raise ValueError("production baseline work_dir must be a dedicated directory")
    try:
        marker = (work_dir / WORK_DIR_MARKER).read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("production baseline work_dir must contain its safety marker") from error
    if marker != WORK_DIR_MARKER_VALUE:
        raise ValueError("production baseline work_dir must contain its safety marker")
    shutil.rmtree(work_dir)


def _remove_owned_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or not path.is_dir():
        raise ValueError("production baseline child work directory must be a directory")
    shutil.rmtree(path)


def _write_evidence(path: Path, evidence: Dict[str, object]) -> None:
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o644)


if __name__ == "__main__":
    raise SystemExit(main())
