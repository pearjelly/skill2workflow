"""Long-running single-instance runtime service boundary."""

from __future__ import annotations

import hmac
import json
import os
import signal
import socket
import sqlite3
import stat
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import urlsplit

from .backup import inspect_state_backup_readiness
from .control_plane import LocalControlPlane
from .credentials import DirectoryCredentialProvider
from .dashboard import MAX_LIVE_SNAPSHOT_BYTES, build_control_snapshot_from_control
from .schedules import RecurringScheduleDispatcher, SchedulerLeaseError
from .state_layout import ensure_service_state_layout, mark_service_state_initialized
from .state_layout import (
    CURRENT_STATE_LAYOUT_VERSION,
    EMPTY_STATE_LAYOUT,
    inspect_state_layout,
    validate_current_state_marker,
)
from .telemetry import RuntimeTelemetry
from .webhooks import MAX_REQUEST_BODY_BYTES, WebhookError, handle_webhook_request


SERVICE_SCHEMA_VERSION = "skill2workflow-service-0.2.0"
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
MAX_AUTH_TOKEN_BYTES = 16 * 1024
LIVE_CONTROL_SNAPSHOT_MAX_ITEMS = 100
MAX_LIVE_CONTROL_SNAPSHOT_BYTES = MAX_LIVE_SNAPSHOT_BYTES


@dataclass(frozen=True)
class ServiceConfig:
    """Validated configuration for the self-hosted runtime service."""

    host: str
    port: int
    state_dir: Path
    storage: str
    auth_token_file: Path
    credential_dir: Path


def load_service_config(path: Path) -> ServiceConfig:
    """Load and validate a versioned service configuration file."""

    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"service config could not be loaded: {config_path}") from error
    return parse_service_config(payload)


def parse_service_config(payload: object) -> ServiceConfig:
    """Validate a decoded service configuration without reading the filesystem."""

    if not isinstance(payload, dict):
        raise ValueError("service config must be a JSON object")
    if set(payload) != {"schema_version", "service", "runtime", "auth", "credentials"}:
        raise ValueError(
            "service config must contain only schema_version, service, runtime, auth, and credentials"
        )
    if payload.get("schema_version") != SERVICE_SCHEMA_VERSION:
        raise ValueError(f"service config schema_version must be {SERVICE_SCHEMA_VERSION}")

    service = payload.get("service")
    runtime = payload.get("runtime")
    auth = payload.get("auth")
    credentials = payload.get("credentials")
    if not isinstance(service, dict) or set(service) != {"host", "port"}:
        raise ValueError("service config service must contain only host and port")
    if not isinstance(runtime, dict) or set(runtime) != {"state_dir", "storage"}:
        raise ValueError("service config runtime must contain only state_dir and storage")
    if not isinstance(auth, dict) or set(auth) != {"provider", "token_file"}:
        raise ValueError("service config auth must contain only provider and token_file")
    if auth.get("provider") != "bearer_token_file":
        raise ValueError("service config auth.provider must be bearer_token_file")
    if not isinstance(credentials, dict) or set(credentials) != {"provider", "directory"}:
        raise ValueError("service config credentials must contain only provider and directory")
    if credentials.get("provider") != "directory":
        raise ValueError("service config credentials.provider must be directory")

    host = service.get("host")
    port = service.get("port")
    state_dir_value = runtime.get("state_dir")
    storage = runtime.get("storage")
    auth_token_file = _absolute_path(auth.get("token_file"), "service auth.token_file")
    credential_dir = _absolute_path(credentials.get("directory"), "service credentials.directory")
    if not isinstance(host, str) or host not in _LOOPBACK_HOSTS:
        raise ValueError(
            "service host must be an explicit loopback address behind the external TLS boundary"
        )
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("service port must be an integer from 0 through 65535")
    if not isinstance(state_dir_value, str) or not state_dir_value.strip():
        raise ValueError("service runtime.state_dir must be a non-empty absolute path")
    state_dir = Path(state_dir_value)
    if not state_dir.is_absolute():
        raise ValueError("service runtime.state_dir must be an absolute path")
    if storage != "sqlite":
        raise ValueError("service runtime.storage must be sqlite")
    return ServiceConfig(
        host=host,
        port=port,
        state_dir=state_dir,
        storage=storage,
        auth_token_file=auth_token_file,
        credential_dir=credential_dir,
    )


class FileBearerTokenAuthenticator:
    """Authenticate one team token from an external file, rereading it per request."""

    def __init__(self, token_file: Path):
        self.token_file = Path(token_file)
        self._read_token()

    def is_ready(self) -> bool:
        try:
            self._read_token()
            return True
        except ValueError:
            return False

    def authenticate(self, authorization: str):
        header = str(authorization or "")
        if not header.startswith("Bearer ") or not header[7:]:
            return False, "missing_or_malformed"
        try:
            expected = self._read_token()
        except ValueError:
            return False, "provider_unavailable"
        supplied = header[7:]
        return (
            (True, "")
            if hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))
            else (False, "invalid")
        )

    def _read_token(self) -> str:
        return read_service_bearer_token(self.token_file)


def read_service_bearer_token(token_file: Path) -> str:
    """Read one private Bearer token through a bounded, identity-checked descriptor."""

    token_file = Path(token_file)
    try:
        details = token_file.lstat()
    except OSError as error:
        raise ValueError("service auth token file is unavailable") from error
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
        raise ValueError("service auth token file must be a regular non-symlink file")
    if stat.S_IMODE(details.st_mode) & 0o077:
        raise ValueError("service auth token file must not be accessible by group or others")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(token_file, flags)
    except OSError as error:
        raise ValueError("service auth token file is unavailable") from error
    try:
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != details.st_dev
                or opened.st_ino != details.st_ino
            ):
                raise ValueError("service auth token file changed while being read")
            if stat.S_IMODE(opened.st_mode) & 0o077:
                raise ValueError(
                    "service auth token file must not be accessible by group or others"
                )
            if opened.st_size > MAX_AUTH_TOKEN_BYTES:
                raise ValueError("service auth token file exceeds the size limit")
            chunks = []
            remaining = MAX_AUTH_TOKEN_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            if len(payload) > MAX_AUTH_TOKEN_BYTES:
                raise ValueError("service auth token file exceeds the size limit")
        except OSError as error:
            raise ValueError("service auth token file is unavailable") from error
    finally:
        os.close(descriptor)
    try:
        token = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("service auth token file is unavailable") from error
    if token.endswith("\r\n"):
        token = token[:-2]
    elif token.endswith("\n"):
        token = token[:-1]
    if len(token.encode("utf-8")) < 32 or "\r" in token or "\n" in token:
        raise ValueError("service auth token must be one line with at least 32 UTF-8 bytes")
    return token


class RuntimeService:
    """Own one local HTTP server and its readiness lifecycle."""

    def __init__(self, config: ServiceConfig, event_logger=None):
        self.config = config
        validate_service_runtime_environment(config)
        ensure_service_state_layout(config.state_dir)
        self.authenticator = FileBearerTokenAuthenticator(config.auth_token_file)
        self.credential_provider = DirectoryCredentialProvider(config.credential_dir)
        self.scheduler = ServiceScheduleLoop(
            config.state_dir,
            credential_provider=self.credential_provider,
        )
        self.control_plane = LocalControlPlane(
            config.state_dir,
            storage=config.storage,
            credential_provider=self.credential_provider,
            execution_owner=self.scheduler.dispatcher.owner_id,
        )
        inspect_state_backup_readiness(
            config.state_dir,
            require_stopped=False,
        )
        mark_service_state_initialized(config.state_dir)
        self.telemetry = RuntimeTelemetry(config.state_dir)
        self.event_logger = event_logger
        self._status = "starting"
        self._server = _http_server(config.host, config.port, _handler_for(self))
        self._server.timeout = 0.2
        self._log_lifecycle("starting")

    @property
    def status(self) -> str:
        return self._status

    @property
    def server_address(self):
        return self._server.server_address

    def readiness(self):
        if self._status != "ready":
            return 503, {"service": "skill2workflow", "status": "not_ready"}
        try:
            if not self.authenticator.is_ready() or not self.credential_provider.is_ready():
                raise ValueError("security provider unavailable")
            if not self.scheduler.is_ready():
                raise ValueError("scheduler lease unavailable")
            self.control_plane.list_workflows()
        except (OSError, sqlite3.Error, ValueError):
            return 503, {"service": "skill2workflow", "status": "not_ready"}
        return 200, {
            "service": "skill2workflow",
            "status": "ready",
            "storage": self.config.storage,
        }

    def begin_shutdown(self) -> None:
        if self._status in {"starting", "ready"}:
            self._status = "draining"
            self._log_lifecycle("draining")

    def serve(self, ready_callback: Optional[Callable[["RuntimeService"], None]] = None) -> None:
        self.scheduler.start()
        self._status = "ready"
        self._log_lifecycle("ready")
        try:
            if ready_callback:
                ready_callback(self)
            while self._status == "ready":
                self._server.handle_request()
        finally:
            self._server.server_close()
            self.scheduler.stop()
            self._status = "stopped"
            self._log_lifecycle("stopped")

    def _log_lifecycle(self, status: str) -> None:
        if self.event_logger is not None:
            self.event_logger.lifecycle(status)


def validate_service_runtime_environment(config: ServiceConfig) -> str:
    """Validate the non-network startup boundary without changing service state."""

    FileBearerTokenAuthenticator(config.auth_token_file)
    _require_private_directory(config.credential_dir, "service credential directory")
    DirectoryCredentialProvider(config.credential_dir)
    return validate_service_state_environment(config)


def validate_service_state_environment(config: ServiceConfig) -> str:
    """Validate only the private, compatible, read-only SQLite state boundary."""

    _require_private_directory(config.state_dir, "service state directory")
    layout = inspect_state_layout(config.state_dir)
    if layout == EMPTY_STATE_LAYOUT:
        return layout
    ensure_service_state_layout(config.state_dir)
    marker = validate_current_state_marker(config.state_dir)
    if not marker["service_initialized"]:
        return EMPTY_STATE_LAYOUT
    inspect_state_backup_readiness(config.state_dir, require_stopped=False)
    if layout != CURRENT_STATE_LAYOUT_VERSION:
        raise ValueError("service state layout is not current")
    return layout


def _require_private_directory(path: Path, label: str) -> None:
    value = Path(path)
    try:
        details = value.lstat()
    except OSError as error:
        raise ValueError(f"{label} must exist") from error
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
        raise ValueError(f"{label} must be a non-symlink directory")
    if stat.S_IMODE(details.st_mode) & 0o077:
        raise ValueError(f"{label} must not be accessible by group or others")


class ServiceScheduleLoop:
    """Keep one dispatcher lease alive and poll recurring schedules off the HTTP thread."""

    def __init__(self, state_dir: Path, credential_provider=None):
        self.dispatcher = RecurringScheduleDispatcher(
            state_dir,
            credential_provider=credential_provider,
            lease_seconds=10,
        )
        self._dispatch_stop = threading.Event()
        self._heartbeat_stop = threading.Event()
        self._dispatch_thread = None
        self._heartbeat_thread = None
        self._last_error = ""

    def start(self) -> None:
        now = time.time()
        if self.dispatcher.try_acquire(now_epoch=now):
            self._recover_after_acquire(now)
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat,
            name="skill2workflow-scheduler-heartbeat",
            daemon=True,
        )
        self._dispatch_thread = threading.Thread(
            target=self._dispatch,
            name="skill2workflow-scheduler-dispatch",
            daemon=True,
        )
        self._heartbeat_thread.start()
        self._dispatch_thread.start()

    def is_ready(self) -> bool:
        return bool(
            self._heartbeat_thread
            and self._heartbeat_thread.is_alive()
            and self._dispatch_thread
            and self._dispatch_thread.is_alive()
            and not self._last_error
            and self.dispatcher.has_lease(now_epoch=time.time())
        )

    def stop(self) -> None:
        self._dispatch_stop.set()
        if self._dispatch_thread:
            self._dispatch_thread.join()
        self._heartbeat_stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join()
        self.dispatcher.release()

    def _heartbeat(self) -> None:
        while not self._heartbeat_stop.is_set():
            if self._last_error:
                self._heartbeat_stop.wait(0.2)
                continue
            try:
                now = time.time()
                if self.dispatcher.has_lease(now_epoch=now):
                    self.dispatcher.renew(now_epoch=now)
                    delay = self.dispatcher.lease_seconds / 3
                else:
                    acquired = self.dispatcher.try_acquire(now_epoch=now)
                    if acquired:
                        self._recover_after_acquire(now)
                    delay = 0.2
            except Exception as error:
                self._record_failure(error)
                delay = 0.2
            self._heartbeat_stop.wait(delay)

    def _dispatch(self) -> None:
        while not self._dispatch_stop.is_set():
            try:
                now_epoch = time.time()
                if self.dispatcher.has_lease(now_epoch=now_epoch):
                    self.dispatcher.dispatch_due(
                        datetime.now(timezone.utc).isoformat(),
                        now_epoch=now_epoch,
                    )
            except SchedulerLeaseError:
                pass
            except Exception as error:
                self._record_failure(error)
            self._dispatch_stop.wait(0.2)

    def _record_failure(self, error: Exception) -> None:
        self._last_error = type(error).__name__
        try:
            self.dispatcher.release()
        except (OSError, sqlite3.Error, ValueError):
            pass

    def _recover_after_acquire(self, now_epoch: float) -> None:
        self.dispatcher.recover_stale_claims(now_epoch=now_epoch)
        self.dispatcher.control_plane.recover_interrupted_runs()


def serve_runtime_service(
    config: ServiceConfig,
    ready_callback: Optional[Callable[[RuntimeService], None]] = None,
    event_logger=None,
) -> None:
    """Serve until SIGINT/SIGTERM or an explicit graceful shutdown request."""

    service = RuntimeService(config, event_logger=event_logger)
    previous_handlers = _install_signal_handlers(service)
    try:
        service.serve(ready_callback=ready_callback)
    finally:
        _restore_signal_handlers(previous_handlers)


def _install_signal_handlers(service: RuntimeService):
    if threading.current_thread() is not threading.main_thread():
        return {}
    previous = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, lambda _signum, _frame: service.begin_shutdown())
    return previous


def _restore_signal_handlers(previous) -> None:
    if threading.current_thread() is not threading.main_thread():
        return
    for signum, handler in previous.items():
        signal.signal(signum, handler)


def _handler_for(service: RuntimeService):
    class RuntimeRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._dispatch_request()

        def do_POST(self):
            self._dispatch_request()

        def do_PUT(self):
            self._dispatch_request()

        def do_DELETE(self):
            self._dispatch_request()

        def _dispatch_request(self):
            started_at = time.monotonic()
            path = urlsplit(self.path).path
            route = _request_route(self.command, path)
            self._response_status = 500
            try:
                if self.command == "GET" and path == "/healthz":
                    self._send_json(200, {"service": "skill2workflow", "status": "ok"})
                elif self.command == "GET" and path == "/readyz":
                    status_code, payload = service.readiness()
                    self._send_json(status_code, payload)
                elif self.command == "GET" and path == "/metrics":
                    self._handle_metrics()
                elif self.command == "GET" and path == "/api/v1/control-snapshot":
                    self._handle_control_snapshot()
                elif self.command == "POST" and _resume_run_id(path):
                    self._handle_resume(_resume_run_id(path))
                elif self.command == "POST" and _cancel_run_id(path):
                    self._handle_cancel(_cancel_run_id(path))
                else:
                    self._handle_webhook()
            finally:
                service.telemetry.observe_http(route, self._response_status)
                if service.event_logger is not None:
                    service.event_logger.request_completed(
                        method=self.command,
                        route=route,
                        status_code=self._response_status,
                        duration_ms=(time.monotonic() - started_at) * 1000,
                    )

        def _handle_metrics(self):
            authenticated, reason = service.authenticator.authenticate(
                self.headers.get("Authorization", "")
            )
            if not authenticated:
                status_code = 503 if reason == "provider_unavailable" else 401
                self._send_json(
                    status_code,
                    {
                        "error": "authentication unavailable"
                        if status_code == 503
                        else "authentication required"
                    },
                    headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
                )
                return
            readiness_status, _ = service.readiness()
            try:
                lease_owned = service.scheduler.dispatcher.has_lease(now_epoch=time.time())
                payload = service.telemetry.render(
                    service_status=service.status,
                    ready=readiness_status == 200,
                    scheduler_lease_owned=lease_owned,
                )
            except (OSError, sqlite3.Error, ValueError):
                self._send_json(503, {"error": "metrics unavailable"})
                return
            self._send_text(200, payload)

        def _handle_control_snapshot(self):
            authenticated, reason = service.authenticator.authenticate(
                self.headers.get("Authorization", "")
            )
            if not authenticated:
                status_code = 503 if reason == "provider_unavailable" else 401
                self._send_json(
                    status_code,
                    {
                        "error": "authentication unavailable"
                        if status_code == 503
                        else "authentication required"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                    if status_code == 401
                    else None,
                )
                return
            try:
                content_length = _content_length(self)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
                return
            if content_length != 0:
                self._send_json(
                    400,
                    {"error": "live control snapshot request must not include a body"},
                )
                return
            try:
                snapshot = build_control_snapshot_from_control(
                    service.control_plane,
                    max_items=LIVE_CONTROL_SNAPSHOT_MAX_ITEMS,
                )
                snapshot_size = len(
                    json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")
                )
                if snapshot_size > MAX_LIVE_CONTROL_SNAPSHOT_BYTES:
                    raise ValueError("control snapshot exceeds response limit")
            except ValueError:
                self._send_json(503, {"error": "control snapshot unavailable"})
                return
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "control snapshot unavailable"})
                return
            self._send_json(200, snapshot)

        def _handle_webhook(self):
            readiness_status, _ = service.readiness()
            if readiness_status != 200:
                self._send_json(503, {"error": "service is not ready"})
                return
            authenticated, reason = service.authenticator.authenticate(
                self.headers.get("Authorization", "")
            )
            route = _request_route(self.command, urlsplit(self.path).path)
            if not authenticated:
                service.control_plane.record_ingress_authentication(
                    False,
                    self.command,
                    route,
                    reason=reason,
                )
                status_code = 503 if reason == "provider_unavailable" else 401
                error_message = (
                    "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                )
                self._send_json(
                    status_code,
                    {"error": error_message},
                    headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
                )
                return
            service.control_plane.record_ingress_authentication(
                True,
                self.command,
                route,
            )
            try:
                body = self.rfile.read(_content_length(self))
                payload = handle_webhook_request(
                    service.control_plane,
                    self.command,
                    self.path,
                    body,
                )
                self._send_json(200, payload)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except ValueError as error:
                self._send_json(400, {"error": str(error)})

        def _handle_cancel(self, run_id: str):
            readiness_status, _ = service.readiness()
            if readiness_status != 200:
                self._send_json(503, {"error": "service is not ready"})
                return
            authenticated, reason = service.authenticator.authenticate(
                self.headers.get("Authorization", "")
            )
            if not authenticated:
                service.control_plane.record_ingress_authentication(
                    False,
                    self.command,
                    "run_cancel",
                    reason=reason,
                )
                status_code = 503 if reason == "provider_unavailable" else 401
                self._send_json(
                    status_code,
                    {
                        "error": "authentication unavailable"
                        if status_code == 503
                        else "authentication required"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                    if status_code == 401
                    else None,
                )
                return
            service.control_plane.record_ingress_authentication(
                True,
                self.command,
                "run_cancel",
            )
            try:
                body = self.rfile.read(_content_length(self))
                if not body:
                    raise ValueError("run cancellation body must be an empty JSON object")
                payload = json.loads(body.decode("utf-8"))
                if payload != {}:
                    raise ValueError("run cancellation body must be an empty JSON object")
                state = service.control_plane.cancel_published_run(run_id)
                self._send_json(
                    200,
                    {"run_id": run_id, "status": str(state["status"])},
                )
            except FileNotFoundError:
                self._send_json(404, {"error": "run not found"})
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "run cancellation body must be valid JSON"})
            except ValueError as error:
                status_code = (
                    409
                    if any(
                        phrase in str(error)
                        for phrase in (
                            "already completed",
                            "already failed",
                            "already interrupted",
                        )
                    )
                    else 400
                )
                self._send_json(status_code, {"error": str(error)})

        def _handle_resume(self, run_id: str):
            readiness_status, _ = service.readiness()
            if readiness_status != 200:
                self._send_json(503, {"error": "service is not ready"})
                return
            authenticated, reason = service.authenticator.authenticate(
                self.headers.get("Authorization", "")
            )
            if not authenticated:
                service.control_plane.record_ingress_authentication(
                    False,
                    self.command,
                    "run_resume",
                    reason=reason,
                )
                status_code = 503 if reason == "provider_unavailable" else 401
                self._send_json(
                    status_code,
                    {
                        "error": "authentication unavailable"
                        if status_code == 503
                        else "authentication required"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                    if status_code == 401
                    else None,
                )
                return
            service.control_plane.record_ingress_authentication(
                True,
                self.command,
                "run_resume",
            )
            try:
                body = self.rfile.read(_content_length(self))
                if not body:
                    raise ValueError("run resume body must contain approved boolean")
                payload = json.loads(body.decode("utf-8"))
                if (
                    not isinstance(payload, dict)
                    or set(payload) != {"approved"}
                    or not isinstance(payload["approved"], bool)
                ):
                    raise ValueError("run resume body must contain approved boolean")
                state = service.control_plane.resume_published_run(
                    run_id,
                    approved=payload["approved"],
                )
                self._send_json(
                    200,
                    {
                        "run_id": run_id,
                        "status": str(state["status"]),
                        "approved": payload["approved"],
                    },
                )
            except FileNotFoundError:
                self._send_json(404, {"error": "run not found"})
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(
                    400,
                    {"error": "run resume body must contain approved boolean"},
                )
            except ValueError as error:
                if str(error).startswith(f"run {run_id} "):
                    self._send_json(409, {"error": "run is not waiting"})
                else:
                    self._send_json(400, {"error": str(error)})

        def _send_json(self, status_code: int, payload: Dict[str, object], headers=None) -> None:
            data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self._response_status = status_code
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            for name, value in (headers or {}).items():
                self.send_header(str(name), str(value))
            self.end_headers()
            self.wfile.write(data)

        def _send_text(self, status_code: int, payload: str) -> None:
            data = payload.encode("utf-8")
            self._response_status = status_code
            self.send_response(status_code)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            return

    return RuntimeRequestHandler


def _request_route(method: str, path: str) -> str:
    if method == "GET" and path == "/healthz":
        return "health"
    if method == "GET" and path == "/readyz":
        return "readiness"
    if method == "GET" and path == "/metrics":
        return "metrics"
    if method == "GET" and path == "/api/v1/control-snapshot":
        return "control_snapshot"
    if path.startswith("/webhooks/"):
        return "workflow_trigger"
    if method == "POST" and _resume_run_id(path):
        return "run_resume"
    if method == "POST" and _cancel_run_id(path):
        return "run_cancel"
    return "unknown"


def _http_server(host: str, port: int, handler):
    class RuntimeHTTPServer(ThreadingHTTPServer):
        daemon_threads = False
        block_on_close = True

    if host == "::1":
        class IPv6HTTPServer(RuntimeHTTPServer):
            address_family = socket.AF_INET6

        return IPv6HTTPServer((host, port), handler)
    return RuntimeHTTPServer((host, port), handler)


def _cancel_run_id(path: str) -> str:
    return _run_action_id(path, "cancel")


def _resume_run_id(path: str) -> str:
    return _run_action_id(path, "resume")


def _run_action_id(path: str, action: str) -> str:
    parts = path.split("/")
    if len(parts) != 4 or parts[0] or parts[1] != "runs" or parts[3] != action:
        return ""
    run_id = parts[2]
    if (
        not run_id.startswith("run_")
        or len(run_id) > 128
        or any(not (char.isalnum() or char in {"_", "-"}) for char in run_id)
    ):
        return ""
    return run_id


def _content_length(handler: BaseHTTPRequestHandler) -> int:
    if handler.headers.get("Transfer-Encoding"):
        raise WebhookError("transfer encoding is not supported", status_code=400)
    content_lengths = handler.headers.get_all("Content-Length", [])
    if len(content_lengths) > 1:
        raise WebhookError("multiple content lengths are not supported", status_code=400)
    raw_value = content_lengths[0] if content_lengths else "0"
    try:
        value = int(raw_value)
    except ValueError:
        raise WebhookError("content length must be a non-negative integer", status_code=400)
    if value < 0:
        raise WebhookError("content length must be a non-negative integer", status_code=400)
    if value > MAX_REQUEST_BODY_BYTES:
        raise WebhookError(
            f"request body exceeds {MAX_REQUEST_BODY_BYTES} bytes",
            status_code=413,
        )
    return value


def _absolute_path(value, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{field} must be an absolute path")
    return path
