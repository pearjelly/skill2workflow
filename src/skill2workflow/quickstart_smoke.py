"""Run the installed-wheel controlled quickstart evidence drill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List


# Wheel qualification builds an isolated virtual environment. On a busy CI
# worker, dependency installation alone can exceed the old 25-second limit.
# Keep a finite bound so an actual stalled build still fails visibly.
PACKAGE_QUALIFICATION_TIMEOUT_SECONDS = 60


def run_quickstart_smoke(
    repo_root: Path, work_dir: Path, reset: bool = True
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    package_work = work_dir / "package"
    package = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "package_smoke.py"),
            "--work-dir",
            str(package_work),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=PACKAGE_QUALIFICATION_TIMEOUT_SECONDS,
    )
    if package.returncode != 0:
        raise RuntimeError("quickstart wheel qualification failed")
    package_result = json.loads(package.stdout)
    console = Path(str(package_result["console_script"]))
    isolated = work_dir / "isolated-user"
    isolated.mkdir(mode=0o700)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    workspace = isolated / "quickstart"
    port = _available_port()
    initialized, raw_initialize = _run_json(
        [
            str(console),
            "quickstart",
            "--root",
            str(workspace),
            "--port",
            str(port),
        ],
        isolated,
        environment,
    )
    custom_skill = isolated / "customer-controlled-review.SKILL.md"
    custom_skill_text = """---
name: installed-customer-review
description: A controlled customer review path.
---

<HARD-GATE>
Do not complete the review before an operator approves it.
</HARD-GATE>

## Checklist

1. Prepare the customer review
2. Ask the operator for approval
3. Record completion
"""
    custom_skill.write_text(custom_skill_text, encoding="utf-8")
    custom_workspace = isolated / "custom-quickstart"
    custom_initialized, raw_custom_initialize = _run_json(
        [
            str(console),
            "quickstart",
            "--root",
            str(custom_workspace),
            "--port",
            str(_available_port()),
            "--skill",
            str(custom_skill),
        ],
        isolated,
        environment,
    )
    custom_workflow_path = custom_workspace / "example" / "workflow.json"
    custom_workflow = json.loads(custom_workflow_path.read_text(encoding="utf-8"))
    custom_workspace_skill = custom_workspace / "example" / "SKILL.md"
    state_dir = Path(str(initialized["state_dir"]))
    config_file = Path(str(initialized["config_file"]))
    ingress_file = Path(str(initialized["token_file"]))
    ingress = ingress_file.read_text(encoding="utf-8").strip()
    redacted = ingress not in raw_initialize
    operator_commands = initialized.get("operator_commands", {})
    expected_commands = {
        "inspect_run": [
            "skill2workflow",
            "control-run",
            str(initialized["run_id"]),
            "--state-dir",
            str(state_dir),
            "--storage",
            "sqlite",
        ],
        "approve_run": [
            "skill2workflow",
            "resume-published",
            str(initialized["run_id"]),
            "--state-dir",
            str(state_dir),
            "--storage",
            "sqlite",
        ],
        "service_doctor": [
            "skill2workflow",
            "service-doctor",
            "--config",
            str(config_file),
        ],
        "start_service": [
            "skill2workflow",
            "service",
            "--config",
            str(config_file),
        ],
    }
    commands_safe = (
        isinstance(operator_commands, dict)
        and all(
            operator_commands.get(name) == command
            for name, command in expected_commands.items()
        )
        and ingress not in json.dumps(operator_commands)
    )

    waiting, _ = _run_json(
        [
            str(console),
            "control-run",
            str(initialized["run_id"]),
            "--state-dir",
            str(state_dir),
            "--storage",
            "sqlite",
        ],
        isolated,
        environment,
    )
    resumed, _ = _run_json(
        [
            str(console),
            "resume-published",
            str(initialized["run_id"]),
            "--state-dir",
            str(state_dir),
            "--storage",
            "sqlite",
        ],
        isolated,
        environment,
    )

    process = subprocess.Popen(
        [str(console), "service", "--config", str(config_file)],
        cwd=str(isolated),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    graceful = False
    try:
        ready = _wait_ready(port, process)
        triggered = _request_json(
            f"http://127.0.0.1:{port}/webhooks/{initialized['workflow_id']}/{initialized['workflow_version']}",
            ingress,
            {
                "source": "installed-quickstart-smoke",
                "idempotency_key": "installed-quickstart-001",
            },
        )
        triggered_run, _ = _run_json(
            [
                str(console),
                "control-run",
                str(triggered["run_id"]),
                "--state-dir",
                str(state_dir),
                "--storage",
                "sqlite",
            ],
            isolated,
            environment,
        )
        process.send_signal(signal.SIGTERM)
        graceful = process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

    checks = {
        "wheel_installed": package_result.get("install_mode") == "wheel",
        "source_imports_disabled": package_result.get("isolated_from_source") is True,
        "quickstart_initialized": initialized.get("status") == "ready_for_review",
        "operator_commands_safe": commands_safe,
        "output_redacted": redacted,
        "skill_compiled_and_published": initialized.get("workflow_id")
        == "workflow_controlled_quickstart",
        "custom_skill_initialized": custom_initialized.get("status")
        == "ready_for_review"
        and custom_initialized.get("run_status") == "waiting"
        and custom_initialized.get("workflow_id")
        == "workflow_installed_customer_review",
        "custom_skill_source_private": (
            str(custom_skill) not in raw_custom_initialize
            and str(custom_skill) not in json.dumps(custom_workflow)
            and custom_workspace_skill.read_text(encoding="utf-8") == custom_skill_text
        ),
        "initial_run_waiting": waiting.get("status") == "waiting",
        "initial_run_resumed": resumed.get("status") == "completed",
        "service_ready": ready,
        "authenticated_trigger_waiting": triggered_run.get("status") == "waiting",
        "graceful_exit": graceful,
    }
    if not all(checks.values()):
        raise RuntimeError("quickstart evidence checks failed")
    return {
        "schema_version": "skill2workflow-quickstart-evidence-0.1.0",
        "status": "passed",
        "checks": checks,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the installed-wheel controlled quickstart drill."
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args(argv)
    result = run_quickstart_smoke(
        args.repo_root, args.work_dir, reset=not args.no_reset
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _run_json(
    command: List[str], cwd: Path, environment: Dict[str, str]
):
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError("installed quickstart command failed")
    return json.loads(completed.stdout), completed.stdout + completed.stderr


def _wait_ready(port: int, process: subprocess.Popen) -> bool:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/readyz", timeout=0.5
            ) as response:
                if int(response.status) == 200:
                    return True
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.05)
    return False


def _request_json(url: str, ingress: str, payload: Dict[str, str]):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {ingress}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _available_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("quickstart smoke work_dir must be outside repository")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("quickstart smoke work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
