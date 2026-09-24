#!/usr/bin/env python3
"""Build and exercise the Linux single-service Docker deployment boundary."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINER_ROOT = "/srv/skill2workflow/team-a"


def _docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=300
    )
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {args[0]}")
    return result.stdout.strip()


def _user_args() -> list[str]:
    return ["--user", f"{os.getuid()}:{os.getgid()}"]


def _runtime_args(workspace: Path) -> list[str]:
    args = [
        "--network", "host",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "128",
        "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=64m",
        *_user_args(),
    ]
    for name in ("config", "secrets", "backups", "state"):
        args.extend(
            [
                "--mount",
                f"type=bind,src={workspace / name},dst={CONTAINER_ROOT}/{name}"
                + ("" if name == "state" else ",readonly"),
            ]
        )
    return args


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _wait_ready(port: int, timeout: float = 25.0) -> None:
    url = f"http://127.0.0.1:{port}/readyz"
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError("Docker service did not become ready")


def _verify_container_boundary(container: str) -> None:
    details = json.loads(_docker("inspect", container))[0]
    if details["HostConfig"]["NetworkMode"] != "host":
        raise RuntimeError("Docker service lost host networking")
    if not details["HostConfig"]["ReadonlyRootfs"]:
        raise RuntimeError("Docker service root filesystem is writable")
    if details["Config"]["User"] != f"{os.getuid()}:{os.getgid()}":
        raise RuntimeError("Docker service is not running as the operator account")
    mounts = {
        mount["Destination"]: mount["RW"]
        for mount in details["Mounts"]
        if mount["Type"] == "bind"
    }
    expected = {
        f"{CONTAINER_ROOT}/{name}": name == "state"
        for name in ("config", "secrets", "backups", "state")
    }
    if mounts != expected:
        raise RuntimeError("Docker service mount write boundary changed")


def main() -> int:
    if sys.platform != "linux" or os.geteuid() == 0:
        raise RuntimeError("Docker smoke requires a non-root Linux operator")
    suffix = uuid.uuid4().hex[:12]
    image = f"skill2workflow:smoke-{suffix}"
    container = f"skill2workflow-smoke-{suffix}"
    _docker("info", "--format", "{{.ServerVersion}}")
    _docker("build", "--tag", image, str(REPO_ROOT))
    try:
        if _docker("image", "inspect", "--format", "{{.Config.User}}", image) != "65532:65532":
            raise RuntimeError("Docker image must default to a non-root user")
        if _docker("run", "--rm", "--network", "none", image, "--version") != "skill2workflow 0.1.0":
            raise RuntimeError("Docker image does not contain the installed CLI")
        with tempfile.TemporaryDirectory(prefix="skill2workflow-docker-") as parent_string:
            parent = Path(parent_string).resolve()
            workspace = parent / "team-a"
            port = _available_port()
            bootstrap = json.loads(
                _docker(
                    "run", "--rm", "--network", "none", *_user_args(),
                    "--mount", f"type=bind,src={parent},dst=/srv/skill2workflow",
                    image, "service-init", "--root", CONTAINER_ROOT,
                    "--host", "127.0.0.1", "--port", str(port),
                )
            )
            if bootstrap.get("status") != "initialized":
                raise RuntimeError("Docker bootstrap did not initialize")
            doctor = json.loads(
                _docker(
                    "run", "--rm", *_runtime_args(workspace), image,
                    "service-doctor", "--config", f"{CONTAINER_ROOT}/config/service.json",
                )
            )
            if doctor.get("status") != "ready":
                raise RuntimeError("Docker Doctor did not pass")

            state_identity = None
            for cycle in range(2):
                _docker(
                    "run", "--detach", "--name", container,
                    *_runtime_args(workspace), image,
                )
                try:
                    _verify_container_boundary(container)
                    _wait_ready(port)
                    gate = json.loads(
                        _docker(
                            "run", "--rm", *_runtime_args(workspace), image,
                            "service-go-live-check", "--config",
                            f"{CONTAINER_ROOT}/config/service.json",
                            "--service-url", f"http://127.0.0.1:{port}",
                            "--auth-token-file", f"{CONTAINER_ROOT}/secrets/ingress-token",
                        )
                    )
                    if gate.get("status") != "ready":
                        raise RuntimeError("Docker go-live gate did not pass")
                finally:
                    _docker("stop", "--time", "20", container)
                    _docker("rm", container)
                current_identity = {
                    path.name: path.stat().st_ino
                    for path in (workspace / "state").glob("*.sqlite3")
                }
                if not current_identity:
                    raise RuntimeError("Docker service did not initialize SQLite state")
                if state_identity is None:
                    state_identity = current_identity
                elif current_identity != state_identity:
                    raise RuntimeError("Docker service did not preserve SQLite files across restart")
            print(json.dumps({"status": "passed", "checks": ["wheel_image", "bootstrap", "doctor", "mount_boundary", "go_live", "restart_persistence"]}))
    finally:
        subprocess.run(["docker", "rm", "--force", container], capture_output=True)
        subprocess.run(["docker", "image", "rm", image], capture_output=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
