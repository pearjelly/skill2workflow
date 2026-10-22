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
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


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
    input_checks = _qualify_input_quickstart(console, isolated, environment)
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
    checks.update(input_checks)
    if not all(checks.values()):
        raise RuntimeError("quickstart evidence checks failed")
    return {
        "schema_version": "skill2workflow-quickstart-evidence-0.1.0",
        "status": "passed",
        "checks": checks,
    }


def _qualify_input_quickstart(console: Path, isolated: Path, environment: Dict[str, str]) -> Dict[str, bool]:
    """Qualify installed typed-input onboarding against one owned HTTP receiver."""
    directory = isolated / 'input-qualification'
    directory.mkdir(mode=0o700)
    payload = {'customer_id': 'quickstart-business-input-canary', 'count': 2}
    requests = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0')))))
            raw = b'{"ok":true,"private":"quickstart-response-canary"}'
            self.send_response(201)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Receiver)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = 'http://127.0.0.1:' + str(server.server_port)
        schema = {'type': 'object', 'properties': {'customer_id': {'type': 'string', 'minLength': 1},
                  'count': {'type': 'integer', 'minimum': 1}},
                  'required': ['customer_id', 'count'], 'additionalProperties': False}
        action = {'request': {'method': 'POST', 'url': origin + '/tasks', 'allowed_origins': [origin],
                  'body': {'source': 'quickstart'}, 'input_mapping': [
                      {'from': '/input/customer_id', 'to': '/body/id'},
                      {'from': '/input/count', 'to': '/body/count'}]}}
        approval = 'Review <!-- skill2workflow: human_gate -->'
        submit = 'Submit <!-- skill2workflow: http ' + json.dumps(action) + ' -->'
        def markdown(steps):
            return ('---\nname: input-quickstart\n---\n<!-- skill2workflow: input_schema '
                    + json.dumps(schema) + ' -->\n## Steps\n'
                    + '\n'.join(str(index) + '. ' + step for index, step in enumerate(steps, 1)) + '\n')
        source = directory / 'private-source.SKILL.md'
        source.write_text(markdown([approval, submit, 'Deliver']), encoding='utf-8')
        input_file = directory / 'private-input.json'
        rejected_root = directory / 'rejected'
        base = [str(console), 'quickstart', '--root', str(rejected_root), '--skill', str(source), '--port', '0']
        refused = []
        for value in (None, {'customer_id': 123, 'count': 2}, dict(payload, extra='invalid-input-canary'), 'malformed'):
            arguments = []
            if value is not None:
                input_file.write_text('{invalid-input-canary}' if value == 'malformed' else json.dumps(value), encoding='utf-8')
                arguments = ['--input', str(input_file)]
            completed = subprocess.run(base + arguments, cwd=str(isolated), env=environment,
                                       capture_output=True, text=True, timeout=10)
            refused.append(completed.returncode == 1 and not rejected_root.exists()
                           and 'invalid-input-canary' not in completed.stdout + completed.stderr)
        input_file.write_text(json.dumps(payload), encoding='utf-8')
        preview, preview_raw = _run_json(base + ['--input', str(input_file), '--dry-run'], isolated, environment)
        preview_ok = (preview.get('ready') is True and not rejected_root.exists() and not requests
                      and payload['customer_id'] not in preview_raw and str(input_file) not in preview_raw
                      and str(source) not in preview_raw and str(rejected_root) not in preview_raw)
        mapping_action = {'request': dict(action['request'], input_mapping=[
            {'from': '/input/customer/id', 'to': '/body/id'}])}
        mapping_source = directory / 'mapping.SKILL.md'
        mapping_source.write_text('---\nname: mapping-quickstart\n---\n## Steps\n1. ' + approval
                                  + '\n2. Submit <!-- skill2workflow: http ' + json.dumps(mapping_action)
                                  + ' -->\n3. Deliver\n', encoding='utf-8')
        mapping_base = [str(console), 'quickstart', '--root', str(rejected_root),
                        '--skill', str(mapping_source), '--port', '0', '--input', str(input_file)]
        blocked_preview = subprocess.run(mapping_base + ['--dry-run'], cwd=str(isolated), env=environment,
                                         capture_output=True, text=True, timeout=10)
        blocked = json.loads(blocked_preview.stdout)
        mapping_refusal = subprocess.run(mapping_base, cwd=str(isolated), env=environment,
                                         capture_output=True, text=True, timeout=10)
        mapping_refused = (blocked_preview.returncode == 1 and blocked.get('ready') is False
                           and any(issue.get('code') == 'required_mapping_input_missing'
                                   for issue in blocked.get('issues', []))
                           and mapping_refusal.returncode == 1
                           and 'required connector mappings' in mapping_refusal.stderr
                           and not rejected_root.exists() and not requests)
        input_file.write_text(json.dumps({'customer': {'id': payload['customer_id']}}), encoding='utf-8')
        corrected, corrected_raw = _run_json(mapping_base + ['--dry-run'], isolated, environment)
        preview_ok = (preview_ok and corrected.get('ready') is True and not rejected_root.exists()
                      and not requests and payload['customer_id'] not in corrected_raw)
        input_file.write_text(json.dumps(payload), encoding='utf-8')
        unsafe = directory / 'unsafe.SKILL.md'
        unsafe.write_text(markdown([submit, approval, 'Deliver']), encoding='utf-8')
        unsafe_root = directory / 'unsafe'
        rejected = subprocess.run([str(console), 'quickstart', '--root', str(unsafe_root),
                                  '--skill', str(unsafe), '--input', str(input_file), '--port', '0'],
                                 cwd=str(isolated), env=environment, capture_output=True, text=True, timeout=10)
        prefix_refused = (rejected.returncode == 1 and not unsafe_root.exists() and not requests
                          and 'before the first human gate' in rejected.stderr)
        accepted_root = directory / 'accepted'
        initialized, raw = _run_json([str(console), 'quickstart', '--root', str(accepted_root),
                                      '--skill', str(source), '--input', str(input_file), '--port', '0'], isolated, environment)
        common = ['--state-dir', str(initialized['state_dir']), '--storage', 'sqlite']
        waiting, _ = _run_json([str(console), 'control-run', initialized['run_id']] + common, isolated, environment)
        waiting_ok = (waiting.get('status') == 'waiting' and waiting.get('context', {}).get('input') == payload
                      and not requests)
        completed, raw_resume = _run_json([str(console), 'resume-published', initialized['run_id']] + common, isolated, environment)
        compact = (payload['customer_id'] not in raw and str(source) not in raw and str(input_file) not in raw
                   and not (accepted_root / 'example' / 'input.json').exists())
        checks = {
            'custom_input_waiting': waiting_ok,
            'invalid_input_no_workspace': all(refused),
            'network_prefix_refused': prefix_refused,
            'custom_input_approved_http': (completed.get('status') == 'completed'
                and requests == [{'source': 'quickstart', 'id': payload['customer_id'], 'count': 2}]
                and 'quickstart-response-canary' not in raw_resume),
            'custom_input_compact_result': compact,
            'quickstart_preview_no_workspace': preview_ok,
            'required_mapping_no_workspace': mapping_refused,
        }
        if not all(checks.values()):
            raise RuntimeError('installed input-aware quickstart qualification failed')
        return checks
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


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
