"""Serve the dependency-free static authoring and control-plane UI."""

from __future__ import annotations

import sysconfig
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional


_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_DATA_ROOT = Path("share") / "skill2workflow"


def find_ui_root() -> Path:
    """Return the repository or installed data root containing the UI assets."""

    candidates = [
        Path(__file__).resolve().parents[2],
        Path(sysconfig.get_path("data")) / _DATA_ROOT,
    ]
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        web_root = candidate / "web"
        examples_root = candidate / "examples"
        if (
            web_root.is_dir()
            and (web_root / "index.html").is_file()
            and (web_root / "control.html").is_file()
            and (examples_root / "control-plane-snapshot.json").is_file()
            and (examples_root / "workflows").is_dir()
        ):
            return candidate
    raise ValueError(
        "skill2workflow UI assets are unavailable; install the complete package "
        "or run from a source checkout"
    )


def serve_ui(
    host: str = "127.0.0.1",
    port: int = 4173,
    *,
    once: bool = False,
    ready_callback: Optional[Callable[[ThreadingHTTPServer], None]] = None,
) -> None:
    """Serve the static UI on a loopback address without accessing runtime state."""

    if str(host).lower() not in _LOOPBACK_HOSTS:
        raise ValueError("UI server must bind to a loopback host")
    root = find_ui_root()

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            return

    handler = partial(QuietHandler, directory=str(root))
    server_class = HTTPServer if once else ThreadingHTTPServer
    server = server_class((host, int(port)), handler)
    try:
        if ready_callback:
            ready_callback(server)
        if once:
            server.handle_request()
        else:
            server.serve_forever()
    finally:
        server.server_close()
