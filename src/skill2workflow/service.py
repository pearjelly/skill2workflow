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
from urllib.parse import parse_qs, unquote, urlsplit

from . import __version__
from .backup import (
    build_state_backup_readiness_report,
    inspect_state_backup_readiness,
)
from .control_plane import LocalControlPlane
from .credentials import DirectoryCredentialProvider
from .dashboard import (
    MAX_LIVE_SNAPSHOT_BYTES,
    MAX_RECURRING_SCHEDULE_LIST_ITEMS,
    MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS,
    MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES,
    MAX_WORKFLOW_INVENTORY_ITEMS,
    MAX_RUN_DETAIL_EVENTS,
    MAX_RUN_LIST_ITEMS,
    MAX_SUPPORT_BUNDLE_BYTES,
    build_control_snapshot_from_control,
    build_recurring_schedule_list_from_store,
    build_recurring_schedule_dispatch_list_from_store,
    build_workflow_artifact_report_from_control,
    build_workflow_inventory_from_control,
    build_run_detail_from_control,
    build_run_list_from_control,
    build_run_page_from_control,
    build_audit_event_page_from_control,
    MAX_AUDIT_EVENT_LIST_ITEMS,
    build_support_bundle_from_control,
)
from .schedules import RecurringScheduleDispatcher, SchedulerLeaseError
from .retention import (
    build_state_retention_readiness_report,
    normalize_retention_policy,
)
from .operational_readiness import (
    OPERATIONAL_READINESS_SCHEMA_VERSION,
    build_operational_readiness_report,
)
from .state_layout import ensure_service_state_layout, mark_service_state_initialized
from .state_layout import (
    CURRENT_STATE_LAYOUT_VERSION,
    EMPTY_STATE_LAYOUT,
    inspect_state_layout,
    validate_current_state_marker,
)
from .telemetry import RuntimeTelemetry
from .triggers import TriggerIdempotencyError
from .webhooks import (
    MAX_REQUEST_BODY_BYTES,
    WebhookError,
    handle_webhook_request,
    read_request_body,
)


SERVICE_SCHEMA_VERSION = "skill2workflow-service-0.2.0"
RUNTIME_INFO_SCHEMA_VERSION = "skill2workflow-runtime-info-0.1.0"
WORKFLOW_DSL_SCHEMA_VERSION = "0.1.0"
WORKFLOW_RELEASE_SCHEMA_VERSION = "skill2workflow-workflow-release-0.1.0"
WORKFLOW_PROMOTION_SCHEMA_VERSION = "skill2workflow-workflow-promotion-0.1.0"
WORKFLOW_DIFF_SCHEMA_VERSION = "skill2workflow-workflow-diff-0.1.0"
WORKFLOW_DEPRECATION_SCHEMA_VERSION = "skill2workflow-workflow-deprecation-0.1.0"
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
MAX_AUTH_TOKEN_BYTES = 16 * 1024
LIVE_CONTROL_SNAPSHOT_MAX_ITEMS = 100
MAX_LIVE_CONTROL_SNAPSHOT_BYTES = MAX_LIVE_SNAPSHOT_BYTES
MAX_RUN_DETAIL_RESPONSE_BYTES = 64 * 1024
MAX_RUN_LIST_RESPONSE_BYTES = 64 * 1024
MAX_RUN_PAGE_RESPONSE_BYTES = 64 * 1024
MAX_AUDIT_EVENT_LIST_RESPONSE_BYTES = 64 * 1024
MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES = 64 * 1024
MAX_RECURRING_SCHEDULE_LIST_RESPONSE_BYTES = 64 * 1024
MAX_RECURRING_SCHEDULE_DISPATCH_LIST_RESPONSE_BYTES = 64 * 1024
MAX_WORKFLOW_ARTIFACT_REPORT_RESPONSE_BYTES = 64 * 1024
MAX_BACKUP_READINESS_RESPONSE_BYTES = 16 * 1024
MAX_AUDIT_INTEGRITY_RESPONSE_BYTES = 16 * 1024
MAX_RUNTIME_INFO_RESPONSE_BYTES = 16 * 1024
MAX_WORKFLOW_RELEASE_RESPONSE_BYTES = 16 * 1024
MAX_WORKFLOW_PROMOTION_RESPONSE_BYTES = 16 * 1024
MAX_WORKFLOW_DIFF_RESPONSE_BYTES = 64 * 1024
MAX_WORKFLOW_DEPRECATION_RESPONSE_BYTES = 16 * 1024
MAX_WORKFLOW_INVENTORY_RESPONSE_BYTES = 64 * 1024
MAX_RETENTION_READINESS_RESPONSE_BYTES = 16 * 1024
MAX_OPERATIONAL_READINESS_RESPONSE_BYTES = 16 * 1024
MAX_RECURRING_SCHEDULE_ACTION_RESPONSE_BYTES = 16 * 1024
MAX_CONCURRENT_BUSINESS_REQUESTS = 16
REQUEST_SOCKET_TIMEOUT_SECONDS = 5.0
WORKFLOW_DEADLINE_SWEEP_INTERVAL_SECONDS = 1.0
MAX_SERVICE_SCHEDULER_BATCH = 100
_MUTATING_REQUEST_ROUTES = frozenset(
    {
        "workflow_trigger",
        "workflow_release",
        "workflow_promotion",
        "workflow_deprecation",
        "recurring_schedule_action",
        "run_resume",
        "run_cancel",
    }
)


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
        self.telemetry = RuntimeTelemetry(config.state_dir)
        self.authenticator = FileBearerTokenAuthenticator(config.auth_token_file)
        self.credential_provider = DirectoryCredentialProvider(config.credential_dir)
        self.scheduler = ServiceScheduleLoop(
            config.state_dir,
            credential_provider=self.credential_provider,
            telemetry=self.telemetry,
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
        self.event_logger = event_logger
        self._request_admission = threading.BoundedSemaphore(
            MAX_CONCURRENT_BUSINESS_REQUESTS
        )
        # Lifecycle transitions can be driven by the serving thread, a signal
        # handler, or an embedding caller.  An RLock keeps the ready/draining
        # decision atomic and remains safe when a signal is delivered while
        # the serving thread already owns the lock.
        self._lifecycle_lock = threading.RLock()
        self._status = "starting"
        self._server = _http_server(config.host, config.port, _handler_for(self))
        self._server.timeout = 0.2
        self._log_lifecycle("starting")

    @property
    def status(self) -> str:
        with self._lifecycle_lock:
            return self._status

    @property
    def server_address(self):
        return self._server.server_address

    def readiness(self):
        if self.status != "ready":
            return 503, {"service": "skill2workflow", "status": "not_ready"}
        try:
            if not self.authenticator.is_ready() or not self.credential_provider.is_ready():
                raise ValueError("security provider unavailable")
            if not self.scheduler.is_ready():
                raise ValueError("scheduler lease unavailable")
            self.control_plane.check_workflow_registry()
        except (OSError, sqlite3.Error, ValueError):
            return 503, {"service": "skill2workflow", "status": "not_ready"}
        return 200, {
            "service": "skill2workflow",
            "status": "ready",
            "storage": self.config.storage,
        }

    def begin_shutdown(self) -> None:
        with self._lifecycle_lock:
            if self._status in {"starting", "ready"}:
                self._status = "draining"
                self.scheduler.stop_dispatching()
                self._log_lifecycle("draining")

    def admit_request(self, route: str) -> str:
        """Atomically decide whether one request may enter the service.

        The lifecycle decision and business-request semaphore acquisition share
        one short critical section.  A request admitted before shutdown may
        finish normally; a mutating request arriving after ``draining`` is
        published is rejected before authentication, body parsing, or any
        control-plane side effect.  Read-only diagnostics remain available for
        shutdown investigation.
        """

        with self._lifecycle_lock:
            if self._status == "draining" and route in _MUTATING_REQUEST_ROUTES:
                return "draining"
            if route in {"health", "readiness"}:
                return "allowed"
            if not self._request_admission.acquire(blocking=False):
                return "busy"
            return "admitted"

    def serve(self, ready_callback: Optional[Callable[["RuntimeService"], None]] = None) -> None:
        had_primary_error = False
        try:
            try:
                self.scheduler.start()
                # Keep the drain check and ready publication atomic.  A
                # signal can arrive after scheduler.start() returns but before
                # the state is written; the lock prevents that request from
                # being overwritten by the normal startup path.
                with self._lifecycle_lock:
                    if self._status == "draining":
                        return
                    self._status = "ready"
                    self._log_lifecycle("ready")
                if ready_callback:
                    ready_callback(self)
                while self.status == "ready":
                    self._server.handle_request()
            except BaseException:
                had_primary_error = True
                raise
        finally:
            cleanup_error = None
            try:
                self._server.server_close()
            except BaseException as error:
                cleanup_error = error
            try:
                self.scheduler.stop()
            except BaseException as error:
                if cleanup_error is None:
                    cleanup_error = error
            finally:
                with self._lifecycle_lock:
                    self._status = "stopped"
                    self._log_lifecycle("stopped")
            if cleanup_error is not None and not had_primary_error:
                raise cleanup_error

    def _log_lifecycle(self, status: str) -> None:
        if self.event_logger is None:
            return
        # Operational logging is deliberately outside the service's control
        # plane.  A broken pipe, closed collector, or user-supplied logger must
        # never prevent startup/teardown or change the lifecycle state.
        try:
            self.event_logger.lifecycle(status)
        except Exception:
            pass


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

    def __init__(self, state_dir: Path, credential_provider=None, telemetry=None):
        self.dispatcher = RecurringScheduleDispatcher(
            state_dir,
            credential_provider=credential_provider,
            lease_seconds=10,
        )
        self.telemetry = telemetry
        self._dispatch_stop = threading.Event()
        self._heartbeat_stop = threading.Event()
        self._dispatch_thread = None
        self._heartbeat_thread = None
        self._last_error = ""
        self._dispatch_gate_lock = threading.RLock()
        self._dispatch_enabled = True
        self._next_workflow_deadline_sweep = 0.0

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
        self.stop_dispatching()
        if self._dispatch_thread:
            self._dispatch_thread.join()
        self._heartbeat_stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join()
        self.dispatcher.release()

    def stop_dispatching(self) -> None:
        """Prevent new recurring dispatches without waiting for an active one."""

        with self._dispatch_gate_lock:
            self._dispatch_enabled = False
            self._dispatch_stop.set()

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
            if not self._admit_dispatch():
                return
            try:
                now_epoch = time.time()
                if self.dispatcher.has_lease(now_epoch=now_epoch):
                    self._sweep_workflow_deadlines(now_epoch)
                    tracked_dispatch = False
                    if self.telemetry is not None:
                        try:
                            tracked_dispatch = self.telemetry.begin_scheduler_dispatch()
                        except Exception:
                            # Operational metrics are best-effort and must not
                            # change recurring-trigger execution semantics.
                            tracked_dispatch = False
                    try:
                        self.dispatcher.dispatch_due(
                            datetime.now(timezone.utc).isoformat(),
                            now_epoch=now_epoch,
                            max_items=MAX_SERVICE_SCHEDULER_BATCH,
                        )
                    finally:
                        if self.telemetry is not None:
                            try:
                                self.telemetry.end_scheduler_dispatch(tracked_dispatch)
                            except Exception:
                                pass
            except SchedulerLeaseError:
                pass
            except Exception as error:
                self._record_failure(error)
            self._dispatch_stop.wait(0.2)

    def _admit_dispatch(self) -> bool:
        """Atomically admit one new recurring dispatch before shutdown."""

        with self._dispatch_gate_lock:
            return self._dispatch_enabled

    def _record_failure(self, error: Exception) -> None:
        self._last_error = type(error).__name__
        try:
            self.dispatcher.release()
        except (OSError, sqlite3.Error, ValueError):
            pass

    def _sweep_workflow_deadlines(self, now_epoch: float, force: bool = False) -> None:
        if not force and float(now_epoch) < self._next_workflow_deadline_sweep:
            return
        self.dispatcher.control_plane.expire_workflow_deadlines(
            now=datetime.now(timezone.utc).isoformat()
        )
        self._next_workflow_deadline_sweep = (
            float(now_epoch) + WORKFLOW_DEADLINE_SWEEP_INTERVAL_SECONDS
        )

    def _recover_after_acquire(self, now_epoch: float) -> None:
        while True:
            recovered = self.dispatcher.recover_stale_claims(
                now_epoch=now_epoch,
                max_items=MAX_SERVICE_SCHEDULER_BATCH,
            )
            if recovered < MAX_SERVICE_SCHEDULER_BATCH:
                break
            if not self.dispatcher.renew(now_epoch=time.time()):
                raise SchedulerLeaseError("scheduler lease was lost during stale-claim recovery")
        while True:
            _recovered, processed = (
                self.dispatcher.control_plane.recover_interrupted_runs_batch(
                    max_items=MAX_SERVICE_SCHEDULER_BATCH
                )
            )
            if processed < MAX_SERVICE_SCHEDULER_BATCH:
                break
            if not self.dispatcher.renew(now_epoch=time.time()):
                raise SchedulerLeaseError(
                    "scheduler lease was lost during interrupted-run recovery"
                )
        after_run_id = ""
        while True:
            _repaired, processed, next_run_id = (
                self.dispatcher.control_plane.reconcile_interrupted_run_audits_batch(
                    max_items=MAX_SERVICE_SCHEDULER_BATCH,
                    after_run_id=after_run_id,
                )
            )
            if processed < MAX_SERVICE_SCHEDULER_BATCH:
                break
            if not next_run_id or next_run_id == after_run_id:
                break
            if not self.dispatcher.renew(now_epoch=time.time()):
                raise SchedulerLeaseError(
                    "scheduler lease was lost during interrupted-run audit reconciliation"
                )
            after_run_id = next_run_id
        self._sweep_workflow_deadlines(now_epoch, force=True)


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
        def setup(self):
            super().setup()
            self.connection.settimeout(REQUEST_SOCKET_TIMEOUT_SECONDS)

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
            self._response_started = False
            admission = service.admit_request(route)
            tracked_request = False
            if admission == "admitted":
                try:
                    tracked_request = service.telemetry.begin_request(route)
                except Exception:
                    # Metrics are best-effort and must never change request
                    # admission or turn a successful handler into a failure.
                    tracked_request = False
            try:
                try:
                    if admission == "draining":
                        self._send_json(
                            503,
                            {"error": "service is draining"},
                            headers={"Retry-After": "1"},
                        )
                    elif admission == "busy":
                        self._send_json(
                            429,
                            {"error": "service concurrency limit reached"},
                            headers={"Retry-After": "1"},
                        )
                    elif self.command == "GET" and path == "/healthz":
                        self._send_json(200, {"service": "skill2workflow", "status": "ok"})
                    elif self.command == "GET" and path == "/readyz":
                        status_code, payload = service.readiness()
                        self._send_json(status_code, payload)
                    elif self.command == "GET" and path == "/metrics":
                        self._handle_metrics()
                    elif self.command == "GET" and path == "/api/v1/control-snapshot":
                        self._handle_control_snapshot()
                    elif self.command == "GET" and path == "/api/v1/workflow-artifacts":
                        self._handle_workflow_artifact_report()
                    elif self.command == "GET" and path == "/api/v1/backup-readiness":
                        self._handle_backup_readiness()
                    elif self.command == "POST" and path == "/api/v1/retention-readiness":
                        self._handle_retention_readiness()
                    elif self.command == "GET" and path == "/api/v1/operational-readiness":
                        self._handle_operational_readiness()
                    elif self.command == "GET" and path == "/api/v1/audit-integrity":
                        self._handle_audit_integrity()
                    elif self.command == "GET" and path == "/api/v1/runtime-info":
                        self._handle_runtime_info()
                    elif self.command == "GET" and path == "/api/v1/workflows":
                        self._handle_workflow_inventory()
                    elif self.command == "POST" and path == "/api/v1/workflow-releases":
                        self._handle_workflow_release()
                    elif self.command == "POST" and path == "/api/v1/workflow-promotions":
                        self._handle_workflow_promotion()
                    elif self.command == "POST" and path == "/api/v1/workflow-deprecations":
                        self._handle_workflow_deprecation()
                    elif self.command == "GET" and _workflow_diff_parts(path) is not None:
                        self._handle_workflow_diff(_workflow_diff_parts(path))
                    elif self.command == "GET" and path == "/api/v1/recurring-schedules":
                        self._handle_recurring_schedule_list()
                    elif self.command == "POST" and _recurring_schedule_action(path):
                        schedule_id, action = _recurring_schedule_action(path)
                        self._handle_recurring_schedule_action(
                            schedule_id,
                            enabled=action == "enable",
                        )
                    elif self.command == "GET" and _recurring_schedule_dispatch_list(path) is not None:
                        self._handle_recurring_schedule_dispatch_list(
                            _recurring_schedule_dispatch_list(path)
                        )
                    elif self.command == "GET" and (
                        path == "/api/v1/audit-consistency"
                        or _audit_consistency_run_id(path)
                    ):
                        self._handle_audit_consistency(_audit_consistency_run_id(path))
                    elif self.command == "GET" and path == "/api/v1/support-bundle":
                        self._handle_support_bundle()
                    elif self.command == "GET" and path == "/runs":
                        self._handle_run_list()
                    elif self.command == "GET" and path == "/api/v1/runs":
                        self._handle_run_page()
                    elif self.command == "GET" and path == "/api/v1/audit-events":
                        self._handle_audit_event_page()
                    elif self.command == "GET" and _run_detail_id(path):
                        self._handle_run_detail(_run_detail_id(path))
                    elif self.command == "POST" and _resume_run_id(path):
                        self._handle_resume(_resume_run_id(path))
                    elif self.command == "POST" and _cancel_run_id(path):
                        self._handle_cancel(_cancel_run_id(path))
                    else:
                        self._handle_webhook()
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    self.close_connection = True
                except Exception:
                    self._send_internal_error()
            finally:
                if admission == "admitted":
                    try:
                        service.telemetry.end_request(tracked_request)
                    except Exception:
                        pass
                    service._request_admission.release()
                try:
                    service.telemetry.observe_http(route, self._response_status)
                except Exception:
                    pass
                if service.event_logger is not None:
                    try:
                        service.event_logger.request_completed(
                            method=self.command,
                            route=route,
                            status_code=self._response_status,
                            duration_ms=(time.monotonic() - started_at) * 1000,
                        )
                    except Exception:
                        pass

        def _send_internal_error(self) -> None:
            """Return one fixed error without exposing unexpected exception details."""

            self.close_connection = True
            if self._response_started:
                return
            try:
                self._send_json(503, {"error": "service unavailable"})
            except (OSError, ValueError):
                self.close_connection = True

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
            try:
                content_length = _content_length(self)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
                return
            if content_length != 0:
                self._send_json(
                    400,
                    {"error": "metrics request must not include a body"},
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

        def _handle_run_detail(self, run_id: str):
            """Serve a bounded status projection for one authenticated run."""

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
                    {"error": "run detail request must not include a body"},
                )
                return
            try:
                detail = build_run_detail_from_control(
                    service.control_plane,
                    run_id,
                    max_events=MAX_RUN_DETAIL_EVENTS,
                )
                encoded = json.dumps(detail, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_RUN_DETAIL_RESPONSE_BYTES:
                    raise ValueError("run detail exceeds response limit")
            except FileNotFoundError:
                self._send_json(404, {"error": "run not found"})
                return
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "run detail unavailable"})
                return
            self._send_json(200, detail)

        def _handle_run_list(self):
            """Serve a bounded, redacted list for run discovery."""

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
                self._send_json(400, {"error": "run list request must not include a body"})
                return
            try:
                payload = build_run_list_from_control(
                    service.control_plane,
                    max_items=MAX_RUN_LIST_ITEMS,
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_RUN_LIST_RESPONSE_BYTES:
                    raise ValueError("run list exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "run list unavailable"})
                return
            self._send_json(200, payload)

        def _handle_run_page(self):
            """Serve a filtered, cursor-paged redacted run projection."""

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
                self._send_json(400, {"error": "run page request must not include a body"})
                return
            try:
                query = _run_page_query(self.path)
                payload = build_run_page_from_control(
                    service.control_plane,
                    max_items=query["max_items"],
                    cursor=query["cursor"],
                    status=query["status"],
                    workflow_id=query["workflow_id"],
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_RUN_PAGE_RESPONSE_BYTES:
                    raise ValueError("run page exceeds response limit")
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "run page unavailable"})
                return
            self._send_json(200, payload)

        def _handle_audit_event_page(self):
            """Serve a bounded, redacted, cursor-paged audit event projection."""

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
                    {"error": "audit event page request must not include a body"},
                )
                return
            try:
                query = _audit_event_page_query(self.path)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return
            try:
                payload = build_audit_event_page_from_control(
                    service.control_plane,
                    max_items=query["max_items"],
                    cursor=query["cursor"],
                    workflow_id=query["workflow_id"],
                    workflow_version=query["workflow_version"],
                    run_id=query["run_id"],
                    event_type=query["event_type"],
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_AUDIT_EVENT_LIST_RESPONSE_BYTES:
                    raise ValueError("audit event page exceeds response limit")
            except ValueError:
                self._send_json(503, {"error": "audit event page unavailable"})
                return
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "audit event page unavailable"})
                return
            self._send_json(200, payload)

        def _handle_recurring_schedule_list(self):
            """Serve a bounded, redacted recurring-schedule inventory."""

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
                    {"error": "recurring schedule list request must not include a body"},
                )
                return
            try:
                payload = build_recurring_schedule_list_from_store(
                    service.scheduler.dispatcher.store,
                    max_items=MAX_RECURRING_SCHEDULE_LIST_ITEMS,
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_RECURRING_SCHEDULE_LIST_RESPONSE_BYTES:
                    raise ValueError("recurring schedule list exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "recurring schedule list unavailable"})
                return
            self._send_json(200, payload)

        def _handle_recurring_schedule_action(self, schedule_id: str, enabled: bool):
            """Apply one authenticated, idempotent recurring-schedule state change."""

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
                    "recurring_schedule_action",
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
                "recurring_schedule_action",
            )
            try:
                body = read_request_body(self)
                if not body:
                    raise ValueError(
                        "recurring schedule action body must be an empty JSON object"
                    )
                payload = json.loads(body.decode("utf-8"))
                if payload != {}:
                    raise ValueError(
                        "recurring schedule action body must be an empty JSON object"
                    )
                definition, changed = (
                    service.scheduler.dispatcher.store.set_enabled_with_result(
                        schedule_id,
                        enabled,
                    )
                )
                service.control_plane.record_recurring_schedule_change(
                    schedule_id,
                    enabled,
                    changed,
                )
                response = {
                    "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
                    "schedule_id": schedule_id,
                    "enabled": bool(definition["schedule"]["enabled"]),
                    "status": str(definition["schedule"]["status"]),
                    "changed": changed,
                }
                encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
                if len(encoded) > MAX_RECURRING_SCHEDULE_ACTION_RESPONSE_BYTES:
                    raise ValueError("recurring schedule action exceeds response limit")
                self._send_json(200, response)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(
                    400,
                    {"error": "recurring schedule action body must be valid JSON"},
                )
            except ValueError as error:
                if "recurring schedule not found" in str(error):
                    self._send_json(404, {"error": "recurring schedule not found"})
                elif "body must" in str(error):
                    self._send_json(400, {"error": str(error)})
                else:
                    self._send_json(503, {"error": "recurring schedule action unavailable"})
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "recurring schedule action unavailable"})

        def _handle_recurring_schedule_dispatch_list(self, schedule_id: str):
            """Serve bounded, redacted recurring dispatch evidence."""

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
                    {"error": "recurring schedule dispatch list request must not include a body"},
                )
                return
            try:
                payload = build_recurring_schedule_dispatch_list_from_store(
                    service.scheduler.dispatcher.store,
                    schedule_id=schedule_id,
                    max_items=MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS,
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_RECURRING_SCHEDULE_DISPATCH_LIST_RESPONSE_BYTES:
                    raise ValueError("recurring schedule dispatch list exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "recurring schedule dispatch list unavailable"})
                return
            self._send_json(200, payload)

        def _handle_workflow_artifact_report(self):
            """Serve a bounded, value-free workflow artifact report."""

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
                    {"error": "workflow artifact report request must not include a body"},
                )
                return
            try:
                payload = build_workflow_artifact_report_from_control(
                    service.control_plane,
                    max_issues=MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES,
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_WORKFLOW_ARTIFACT_REPORT_RESPONSE_BYTES:
                    raise ValueError("workflow artifact report exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "workflow artifact report unavailable"})
                return
            self._send_json(200, payload)

        def _handle_workflow_inventory(self):
            """Serve bounded published-version metadata without workflow content."""

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
                    {"error": "workflow inventory request must not include a body"},
                )
                return
            try:
                payload = build_workflow_inventory_from_control(
                    service.control_plane,
                    max_items=MAX_WORKFLOW_INVENTORY_ITEMS,
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_WORKFLOW_INVENTORY_RESPONSE_BYTES:
                    raise ValueError("workflow inventory exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "workflow inventory unavailable"})
                return
            self._send_json(200, payload)

        def _handle_backup_readiness(self):
            """Serve fixed read-only preflight data for an offline backup."""

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
                    {"error": "backup readiness request must not include a body"},
                )
                return
            try:
                payload = build_state_backup_readiness_report(service.config.state_dir)
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_BACKUP_READINESS_RESPONSE_BYTES:
                    raise ValueError("backup readiness exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "backup readiness unavailable"})
                return
            self._send_json(200, payload)

        def _handle_retention_readiness(self):
            """Serve a policy-bound, read-only retention preflight."""

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
                body = read_request_body(self)
                payload = json.loads(body.decode("utf-8"))
                if (
                    not isinstance(payload, dict)
                    or set(payload) != {"policy"}
                    or not isinstance(payload.get("policy"), dict)
                ):
                    raise ValueError(
                        "retention readiness request must contain one policy object"
                    )
                policy = normalize_retention_policy(payload["policy"])
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
                return
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
                OverflowError,
                RecursionError,
            ):
                self._send_json(400, {"error": "retention readiness rejected"})
                return
            try:
                report = build_state_retention_readiness_report(
                    service.config.state_dir,
                    policy,
                )
                encoded = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_RETENTION_READINESS_RESPONSE_BYTES:
                    raise ValueError("retention readiness exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "retention readiness unavailable"})
                return
            self._send_json(200, report)

        def _handle_operational_readiness(self):
            """Serve one aggregate, redacted operator readiness report."""

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
                    {"error": "operational readiness request must not include a body"},
                )
                return
            try:
                report = build_operational_readiness_report(service)
                if report.get("schema_version") != OPERATIONAL_READINESS_SCHEMA_VERSION:
                    raise ValueError("operational readiness schema is invalid")
                encoded = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_OPERATIONAL_READINESS_RESPONSE_BYTES:
                    raise ValueError("operational readiness exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "operational readiness unavailable"})
                return
            self._send_json(200, report)

        def _handle_audit_integrity(self):
            """Serve the fixed, payload-free SQLite audit-chain result."""

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
                    {"error": "audit integrity request must not include a body"},
                )
                return
            try:
                payload = service.control_plane.verify_audit_integrity()
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_AUDIT_INTEGRITY_RESPONSE_BYTES:
                    raise ValueError("audit integrity exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "audit integrity unavailable"})
                return
            self._send_json(200, payload)

        def _handle_runtime_info(self):
            """Serve fixed runtime identity and compatibility metadata."""

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
                    {"error": "runtime info request must not include a body"},
                )
                return
            try:
                readiness_status, _ = service.readiness()
                payload = {
                    "schema_version": RUNTIME_INFO_SCHEMA_VERSION,
                    "package_version": __version__,
                    "compatibility_line": "0.1.x",
                    "service_schema_version": SERVICE_SCHEMA_VERSION,
                    "workflow_dsl_schema_version": WORKFLOW_DSL_SCHEMA_VERSION,
                    "storage": service.config.storage,
                    "state_layout_version": inspect_state_layout(
                        service.config.state_dir
                    ),
                    "service_status": service.status,
                    "service_ready": readiness_status == 200,
                    "scheduler_lease_owned": bool(
                        service.scheduler.dispatcher.has_lease(now_epoch=time.time())
                    ),
                }
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_RUNTIME_INFO_RESPONSE_BYTES:
                    raise ValueError("runtime info exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "runtime info unavailable"})
                return
            self._send_json(200, payload)

        def _handle_workflow_release(self):
            """Publish one validated immutable workflow through the service."""

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
                    "workflow_release",
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
                "workflow_release",
            )
            try:
                body = read_request_body(self)
                payload = json.loads(body.decode("utf-8"))
                if (
                    not isinstance(payload, dict)
                    or set(payload) != {"workflow"}
                    or not isinstance(payload.get("workflow"), dict)
                ):
                    raise ValueError("workflow release request must contain one workflow object")
                record = service.control_plane.publish_workflow(payload["workflow"])
                response = {
                    "schema_version": WORKFLOW_RELEASE_SCHEMA_VERSION,
                    "workflow_id": str(record.get("workflow_id", "")),
                    "version": str(record.get("version", "")),
                    "status": str(record.get("status", "")),
                    "checksum": str(record.get("checksum", "")),
                }
                encoded = json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_WORKFLOW_RELEASE_RESPONSE_BYTES:
                    raise ValueError("workflow release response exceeds response limit")
                self._send_json(200, response)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, OverflowError, RecursionError) as error:
                if "immutable" in str(error).lower():
                    self._send_json(409, {"error": "workflow version is immutable"})
                else:
                    self._send_json(400, {"error": "workflow publication rejected"})
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "workflow publication unavailable"})

        def _handle_workflow_promotion(self):
            """Move one stable alias through the authenticated service boundary."""

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
                    "workflow_promotion",
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
                "workflow_promotion",
            )
            try:
                body = read_request_body(self)
                payload = json.loads(body.decode("utf-8"))
                fields = {
                    "workflow_id",
                    "version",
                    "alias",
                    "expected_current_version",
                }
                if (
                    not isinstance(payload, dict)
                    or set(payload) != fields
                    or any(not isinstance(payload.get(field), str) for field in fields)
                ):
                    raise ValueError("workflow promotion request is malformed")
                if not payload["expected_current_version"]:
                    expected_current_version = ""
                else:
                    expected_current_version = payload["expected_current_version"]
                record = service.control_plane.promote_workflow(
                    payload["workflow_id"],
                    payload["version"],
                    alias=payload["alias"],
                    expected_current_version=expected_current_version,
                )
                aliases = record.get("aliases", [])
                if not isinstance(aliases, list) or payload["alias"] not in aliases:
                    raise ValueError("workflow promotion did not retain alias")
                response = {
                    "schema_version": WORKFLOW_PROMOTION_SCHEMA_VERSION,
                    "workflow_id": str(record.get("workflow_id", "")),
                    "version": str(record.get("version", "")),
                    "alias": payload["alias"],
                    "status": "promoted",
                    "checksum": str(record.get("checksum", "")),
                }
                encoded = json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_WORKFLOW_PROMOTION_RESPONSE_BYTES:
                    raise ValueError("workflow promotion response exceeds response limit")
                self._send_json(200, response)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except ValueError as error:
                message = str(error).lower()
                if "precondition failed" in message:
                    self._send_json(409, {"error": "workflow alias precondition failed"})
                elif "version not found" in message:
                    self._send_json(404, {"error": "workflow version not found"})
                elif "not published" in message:
                    self._send_json(409, {"error": "workflow version is not published"})
                else:
                    self._send_json(400, {"error": "workflow promotion rejected"})
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, OverflowError, RecursionError):
                self._send_json(400, {"error": "workflow promotion rejected"})
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "workflow promotion unavailable"})

        def _handle_workflow_deprecation(self):
            """Deprecate one published workflow version through the service."""

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
                    "workflow_deprecation",
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
                "workflow_deprecation",
            )
            try:
                body = read_request_body(self)
                payload = json.loads(body.decode("utf-8"))
                fields = {"workflow_id", "version"}
                if (
                    not isinstance(payload, dict)
                    or set(payload) != fields
                    or any(
                        not isinstance(payload.get(field), str) or not payload.get(field)
                        for field in fields
                    )
                ):
                    raise ValueError("workflow deprecation request is malformed")
                record = service.control_plane.deprecate_workflow(
                    payload["workflow_id"],
                    payload["version"],
                )
                response = {
                    "schema_version": WORKFLOW_DEPRECATION_SCHEMA_VERSION,
                    "workflow_id": str(record.get("workflow_id", "")),
                    "version": str(record.get("version", "")),
                    "status": str(record.get("status", "")),
                    "checksum": str(record.get("checksum", "")),
                }
                encoded = json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_WORKFLOW_DEPRECATION_RESPONSE_BYTES:
                    raise ValueError("workflow deprecation response exceeds response limit")
                if response["status"] != "deprecated":
                    raise ValueError("workflow deprecation did not persist status")
                self._send_json(200, response)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except ValueError as error:
                if "version not found" in str(error).lower():
                    self._send_json(404, {"error": "workflow version not found"})
                else:
                    self._send_json(400, {"error": "workflow deprecation rejected"})
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, OverflowError, RecursionError):
                self._send_json(400, {"error": "workflow deprecation rejected"})
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "workflow deprecation unavailable"})

        def _handle_workflow_diff(self, parts):
            """Serve a bounded, value-free diff of two published versions."""

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
                if _content_length(self) != 0:
                    self._send_json(
                        400,
                        {"error": "workflow diff request must not include a body"},
                    )
                    return
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
                return
            workflow_id, from_version, to_version = parts
            try:
                payload = service.control_plane.diff_workflow_versions(
                    workflow_id,
                    from_version,
                    to_version,
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_WORKFLOW_DIFF_RESPONSE_BYTES:
                    raise ValueError("workflow diff exceeds response limit")
            except ValueError as error:
                message = str(error).lower()
                if "version not found" in message:
                    self._send_json(404, {"error": "workflow version not found"})
                elif "artifact unavailable" in message:
                    self._send_json(503, {"error": "workflow diff unavailable"})
                else:
                    self._send_json(503, {"error": "workflow diff unavailable"})
                return
            except (OSError, sqlite3.Error):
                self._send_json(503, {"error": "workflow diff unavailable"})
                return
            self._send_json(200, payload)

        def _handle_audit_consistency(self, run_id: str = ""):
            """Serve the bounded, value-free run/audit consistency projection."""

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
                    {"error": "audit consistency request must not include a body"},
                )
                return
            try:
                payload = service.control_plane.inspect_run_audit(run_id=run_id)
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES:
                    raise ValueError("audit consistency exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "audit consistency unavailable"})
                return
            self._send_json(200, payload)

        def _handle_support_bundle(self):
            """Serve one bounded, redacted diagnostic package."""

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
                    {"error": "support bundle request must not include a body"},
                )
                return
            try:
                readiness_status, _ = service.readiness()
                lease_owned = service.scheduler.dispatcher.has_lease(now_epoch=time.time())
                payload = build_support_bundle_from_control(
                    service.control_plane,
                    service.telemetry,
                    service_status=service.status,
                    ready=readiness_status == 200,
                    scheduler_lease_owned=lease_owned,
                    storage=service.config.storage,
                )
                encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                if len(encoded) > MAX_SUPPORT_BUNDLE_BYTES:
                    raise ValueError("support bundle exceeds response limit")
            except (ValueError, OSError, sqlite3.Error):
                self._send_json(503, {"error": "support bundle unavailable"})
                return
            self._send_json(200, payload)

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
                body = read_request_body(self)
                payload = handle_webhook_request(
                    service.control_plane,
                    self.command,
                    self.path,
                    body,
                )
                self._send_json(200, payload)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except TriggerIdempotencyError as error:
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
                body = read_request_body(self)
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
                body = read_request_body(self)
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
            self._response_started = True
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            for name, value in (headers or {}).items():
                self.send_header(str(name), str(value))
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()

        def _send_text(self, status_code: int, payload: str) -> None:
            data = payload.encode("utf-8")
            self._response_status = status_code
            self._response_started = True
            self.send_response(status_code)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()

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
    if method == "GET" and path == "/api/v1/workflow-artifacts":
        return "workflow_artifact_report"
    if method == "GET" and path == "/api/v1/backup-readiness":
        return "backup_readiness"
    if method == "POST" and path == "/api/v1/retention-readiness":
        return "retention_readiness"
    if method == "GET" and path == "/api/v1/operational-readiness":
        return "operational_readiness"
    if method == "GET" and path == "/api/v1/audit-integrity":
        return "audit_integrity"
    if method == "GET" and path == "/api/v1/runtime-info":
        return "runtime_info"
    if method == "GET" and path == "/api/v1/workflows":
        return "workflow_inventory"
    if method == "POST" and path == "/api/v1/workflow-releases":
        return "workflow_release"
    if method == "POST" and path == "/api/v1/workflow-promotions":
        return "workflow_promotion"
    if method == "POST" and path == "/api/v1/workflow-deprecations":
        return "workflow_deprecation"
    if method == "GET" and _workflow_diff_parts(path) is not None:
        return "workflow_diff"
    if method == "GET" and path == "/api/v1/recurring-schedules":
        return "recurring_schedule_list"
    if method == "GET" and _recurring_schedule_dispatch_list(path) is not None:
        return "recurring_schedule_dispatch_list"
    if method == "POST" and _recurring_schedule_action(path):
        return "recurring_schedule_action"
    if method == "GET" and path == "/api/v1/audit-consistency":
        return "audit_consistency"
    if method == "GET" and _audit_consistency_run_id(path):
        return "audit_consistency"
    if method == "GET" and path == "/api/v1/support-bundle":
        return "support_bundle"
    if method == "GET" and path == "/runs":
        return "run_list"
    if method == "GET" and path == "/api/v1/runs":
        return "run_page"
    if method == "GET" and path == "/api/v1/audit-events":
        return "audit_event_list"
    if method == "GET" and _run_detail_id(path):
        return "run_detail"
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


def _recurring_schedule_action(path: str):
    parts = path.split("/")
    if (
        len(parts) != 6
        or parts[:4] != ["", "api", "v1", "recurring-schedules"]
        or parts[5] not in {"enable", "disable"}
    ):
        return None
    schedule_id = parts[4]
    if (
        not schedule_id
        or len(schedule_id) > 128
        or any(not (char.isalnum() or char in {"-", "_", "."}) for char in schedule_id)
    ):
        return None
    return schedule_id, parts[5]


def _recurring_schedule_dispatch_list(path: str):
    if path == "/api/v1/recurring-schedule-dispatches":
        return ""
    parts = path.split("/")
    if (
        len(parts) != 6
        or parts[:4] != ["", "api", "v1", "recurring-schedules"]
        or parts[5] != "dispatches"
    ):
        return None
    schedule_id = parts[4]
    if (
        not schedule_id
        or len(schedule_id) > 128
        or any(not (char.isalnum() or char in {"-", "_", "."}) for char in schedule_id)
    ):
        return None
    return schedule_id


def _cancel_run_id(path: str) -> str:
    return _run_action_id(path, "cancel")


def _resume_run_id(path: str) -> str:
    return _run_action_id(path, "resume")


def _run_detail_id(path: str) -> str:
    parts = path.split("/")
    if len(parts) != 3 or parts[0] or parts[1] != "runs":
        return ""
    run_id = parts[2]
    if (
        not run_id.startswith("run_")
        or len(run_id) > 128
        or any(not (char.isalnum() or char in {"_", "-"}) for char in run_id)
    ):
        return ""
    return run_id


def _run_page_query(request_path: str) -> Dict[str, object]:
    """Parse the bounded query contract for filtered run discovery."""

    try:
        query = parse_qs(
            urlsplit(str(request_path)).query,
            keep_blank_values=True,
            max_num_fields=8,
        )
    except ValueError as error:
        raise ValueError("run page query is invalid") from error
    allowed = {"cursor", "max_items", "status", "workflow_id"}
    if any(key not in allowed for key in query):
        raise ValueError("run page query contains an unsupported field")

    def one(key: str) -> str:
        values = query.get(key, [""])
        if len(values) != 1:
            raise ValueError(f"run page query field {key} must appear once")
        return str(values[0])

    raw_limit = one("max_items") or "100"
    try:
        max_items = int(raw_limit)
    except (TypeError, ValueError) as error:
        raise ValueError("run page max_items must be an integer") from error
    return {
        "cursor": one("cursor"),
        "max_items": max_items,
        "status": one("status"),
        "workflow_id": one("workflow_id"),
    }


def _audit_event_page_query(request_path: str) -> Dict[str, object]:
    """Parse the bounded query contract for remote audit event pages."""

    try:
        query = parse_qs(
            urlsplit(str(request_path)).query,
            keep_blank_values=True,
            max_num_fields=12,
        )
    except ValueError as error:
        raise ValueError("audit event query is invalid") from error
    allowed = {
        "cursor", "max_items", "workflow_id", "workflow_version", "run_id", "event_type"
    }
    if any(key not in allowed for key in query):
        raise ValueError("audit event query contains an unsupported field")

    def one(key: str) -> str:
        values = query.get(key, [""])
        if len(values) != 1:
            raise ValueError(f"audit event query field {key} must appear once")
        return str(values[0])

    raw_limit = one("max_items") or str(MAX_AUDIT_EVENT_LIST_ITEMS)
    try:
        max_items = int(raw_limit)
    except (TypeError, ValueError) as error:
        raise ValueError("audit event max_items must be an integer") from error
    return {
        "cursor": one("cursor"),
        "max_items": max_items,
        "workflow_id": one("workflow_id"),
        "workflow_version": one("workflow_version"),
        "run_id": one("run_id"),
        "event_type": one("event_type"),
    }


def _audit_consistency_run_id(path: str) -> str:
    parts = path.split("/")
    if len(parts) != 5 or parts[:3] != ["", "api", "v1"] or parts[3] != "audit-consistency":
        return ""
    run_id = parts[4]
    if (
        not run_id.startswith("run_")
        or len(run_id) > 128
        or any(not (char.isalnum() or char in {"_", "-"}) for char in run_id)
    ):
        return ""
    return run_id


def _workflow_diff_parts(path: str):
    parts = path.split("/")
    if len(parts) != 7 or parts[:4] != ["", "api", "v1", "workflow-diffs"]:
        return None
    values = tuple(unquote(value) for value in parts[4:])
    if any(not value or len(value) > 128 for value in values):
        return None
    if any(
        any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
        for value in values
    ):
        return None
    return values


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
