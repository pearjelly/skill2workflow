"""Serve the dependency-free static authoring and control-plane UI."""

from __future__ import annotations

import json
import re
import sysconfig
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, unquote, urlsplit

from .dashboard import MAX_LIVE_SNAPSHOT_BYTES
from .live_snapshot import fetch_live_control_snapshot
from .service import read_service_bearer_token
from .service_client import (
    MAX_SERVICE_ACTION_RESPONSE_BYTES,
    MAX_OPERATIONAL_READINESS_RESPONSE_BYTES,
    MAX_RECURRING_SCHEDULE_DISPATCH_PAGE_ITEMS,
    MAX_RECURRING_SCHEDULE_DISPATCH_PAGE_RESPONSE_BYTES,
    MAX_RECURRING_SCHEDULE_DISPATCH_REVIEW_REQUEST_BYTES,
    MAX_RECURRING_SCHEDULE_DISPATCH_REVIEW_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_EXPLANATION_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_DIFF_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_RELEASE_REQUEST_BYTES,
    MAX_REMOTE_WORKFLOW_RELEASE_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_RELEASE_PREFLIGHT_REQUEST_BYTES,
    MAX_REMOTE_WORKFLOW_RELEASE_PREFLIGHT_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_DEPRECATION_REQUEST_BYTES,
    MAX_REMOTE_WORKFLOW_DEPRECATION_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_INVENTORY_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_PROMOTION_REQUEST_BYTES,
    MAX_REMOTE_WORKFLOW_PROMOTION_RESPONSE_BYTES,
    MAX_REMOTE_WORKFLOW_PREFLIGHT_REQUEST_BYTES,
    MAX_REMOTE_WORKFLOW_PREFLIGHT_RESPONSE_BYTES,
    MAX_SERVICE_PROBE_RESPONSE_BYTES,
    MAX_SUPPORT_BUNDLE_RESPONSE_BYTES,
    ServiceActionError,
    fetch_audit_events,
    fetch_recurring_schedule_list,
    fetch_recurring_schedule_dispatch_page,
    post_recurring_schedule_dispatch_review,
    fetch_run_detail,
    fetch_run_page,
    fetch_operational_readiness,
    fetch_support_bundle,
    fetch_service_probe,
    fetch_workflow_inventory,
    fetch_workflow_explanation,
    fetch_workflow_diff,
    fetch_workflow_preflight,
    post_workflow_release,
    post_workflow_release_preflight,
    post_workflow_promotion,
    post_workflow_deprecation,
    post_run_resume,
    post_run_cancel,
    service_endpoint,
)


_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_DATA_ROOT = Path("share") / "skill2workflow"
_LIVE_SNAPSHOT_PATH = "/api/v1/control-snapshot"
_LIVE_SNAPSHOT_MAX_RESPONSE_BYTES = MAX_LIVE_SNAPSHOT_BYTES
_SERVICE_PROBE_PATH = "/api/v1/service-probe"
_SERVICE_PROBE_MAX_RESPONSE_BYTES = MAX_SERVICE_PROBE_RESPONSE_BYTES
_OPERATIONAL_READINESS_PATH = "/api/v1/operational-readiness"
_OPERATIONAL_READINESS_MAX_RESPONSE_BYTES = MAX_OPERATIONAL_READINESS_RESPONSE_BYTES
_WORKFLOW_INVENTORY_PATH = "/api/v1/workflows"
_WORKFLOW_INVENTORY_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_INVENTORY_RESPONSE_BYTES
_WORKFLOW_EXPLANATION_PREFIX = "/api/v1/workflow-explanations/"
_WORKFLOW_EXPLANATION_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_EXPLANATION_RESPONSE_BYTES
_WORKFLOW_DIFF_PREFIX = "/api/v1/workflow-diffs/"
_WORKFLOW_DIFF_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_DIFF_RESPONSE_BYTES
_WORKFLOW_PREFLIGHT_PREFIX = "/api/v1/workflow-preflights/"
_WORKFLOW_PREFLIGHT_MAX_REQUEST_BYTES = min(16, MAX_REMOTE_WORKFLOW_PREFLIGHT_REQUEST_BYTES)
_WORKFLOW_PREFLIGHT_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_PREFLIGHT_RESPONSE_BYTES
_WORKFLOW_RELEASE_PATH = "/api/v1/workflow-releases"
_WORKFLOW_RELEASE_MAX_REQUEST_BYTES = MAX_REMOTE_WORKFLOW_RELEASE_REQUEST_BYTES
_WORKFLOW_RELEASE_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_RELEASE_RESPONSE_BYTES
_WORKFLOW_RELEASE_PREFLIGHT_PATH = "/api/v1/workflow-release-preflights"
_WORKFLOW_RELEASE_PREFLIGHT_MAX_REQUEST_BYTES = MAX_REMOTE_WORKFLOW_RELEASE_PREFLIGHT_REQUEST_BYTES
_WORKFLOW_RELEASE_PREFLIGHT_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_RELEASE_PREFLIGHT_RESPONSE_BYTES
_WORKFLOW_PROMOTION_PATH = "/api/v1/workflow-promotions"
_WORKFLOW_PROMOTION_MAX_REQUEST_BYTES = min(512, MAX_REMOTE_WORKFLOW_PROMOTION_REQUEST_BYTES)
_WORKFLOW_PROMOTION_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_PROMOTION_RESPONSE_BYTES
_WORKFLOW_DEPRECATION_PATH = "/api/v1/workflow-deprecations"
_WORKFLOW_DEPRECATION_MAX_REQUEST_BYTES = min(512, MAX_REMOTE_WORKFLOW_DEPRECATION_REQUEST_BYTES)
_WORKFLOW_DEPRECATION_MAX_RESPONSE_BYTES = MAX_REMOTE_WORKFLOW_DEPRECATION_RESPONSE_BYTES
_WORKFLOW_ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_SUPPORT_BUNDLE_PATH = "/api/v1/support-bundle"
_SUPPORT_BUNDLE_MAX_RESPONSE_BYTES = MAX_SUPPORT_BUNDLE_RESPONSE_BYTES
_LIVE_RESUME_PREFIX = "/api/v1/runs/"
_LIVE_RESUME_SUFFIX = "/resume"
_LIVE_RESUME_MAX_REQUEST_BYTES = 128
_LIVE_CANCEL_SUFFIX = "/cancel"
_LIVE_CANCEL_MAX_REQUEST_BYTES = 16
_LIVE_RUN_DETAIL_PREFIX = "/api/v1/runs/"
_LIVE_RUN_DETAIL_MAX_RESPONSE_BYTES = MAX_SERVICE_ACTION_RESPONSE_BYTES
_LIVE_RUN_PAGE_PATH = "/api/v1/run-page"
_LIVE_RUN_PAGE_MAX_RESPONSE_BYTES = MAX_SERVICE_ACTION_RESPONSE_BYTES
_LIVE_RUN_PAGE_MAX_ITEMS = 100
_LIVE_AUDIT_PAGE_PATH = "/api/v1/audit-page"
_LIVE_AUDIT_PAGE_MAX_RESPONSE_BYTES = MAX_SERVICE_ACTION_RESPONSE_BYTES
_LIVE_AUDIT_PAGE_MAX_ITEMS = 100
_LIVE_SCHEDULE_LIST_PATH = "/api/v1/recurring-schedules"
_LIVE_SCHEDULE_LIST_MAX_RESPONSE_BYTES = MAX_SERVICE_ACTION_RESPONSE_BYTES
_LIVE_SCHEDULE_DISPATCH_PAGE_PREFIX = "/api/v1/recurring-schedule-dispatch-pages/"
_LIVE_SCHEDULE_DISPATCH_PAGE_MAX_ITEMS = MAX_RECURRING_SCHEDULE_DISPATCH_PAGE_ITEMS
_LIVE_SCHEDULE_DISPATCH_PAGE_MAX_RESPONSE_BYTES = MAX_RECURRING_SCHEDULE_DISPATCH_PAGE_RESPONSE_BYTES
_LIVE_SCHEDULE_DISPATCH_REVIEW_PREFIX = "/api/v1/recurring-schedule-dispatch-reviews/"
_LIVE_SCHEDULE_DISPATCH_REVIEW_MAX_REQUEST_BYTES = min(
    512,
    MAX_RECURRING_SCHEDULE_DISPATCH_REVIEW_REQUEST_BYTES,
)
_LIVE_SCHEDULE_DISPATCH_REVIEW_MAX_RESPONSE_BYTES = MAX_RECURRING_SCHEDULE_DISPATCH_REVIEW_RESPONSE_BYTES


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
    service_url: Optional[str] = None,
    auth_token_file: Optional[Path] = None,
) -> None:
    """Serve the UI, optionally adding fixed authenticated live routes.

    Static mode never accesses runtime state. Live mode is opt-in and keeps the
    Bearer token server-side: the browser can request only the fixed documented
    snapshot, diagnostics, and confirmation-protected operator-action paths,
    while the UI process reads the owner-only token file per request.
    """

    if str(host).lower() not in _LOOPBACK_HOSTS:
        raise ValueError("UI server must bind to a loopback host")
    if (service_url is None) != (auth_token_file is None):
        raise ValueError("live UI mode requires both --service-url and --auth-token-file")
    if service_url is not None:
        service_endpoint(service_url, _LIVE_SNAPSHOT_PATH)
        read_service_bearer_token(Path(auth_token_file))
    root = find_ui_root()

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == _LIVE_RUN_PAGE_PATH:
                try:
                    cursor = _parse_live_run_page_cursor(parsed.query)
                except ValueError:
                    self._write_json(404, {"error": "run page path is not available"})
                    return
                self._serve_live_run_page(cursor)
                return
            if parsed.path == _LIVE_AUDIT_PAGE_PATH:
                try:
                    cursor = _parse_live_audit_page_cursor(parsed.query)
                except ValueError:
                    self._write_json(404, {"error": "audit page path is not available"})
                    return
                self._serve_live_audit_page(cursor)
                return
            if parsed.path == _LIVE_SCHEDULE_LIST_PATH:
                if parsed.query:
                    self._write_json(404, {"error": "schedule list path is not available"})
                    return
                self._serve_live_schedule_list()
                return
            if parsed.path.startswith(_LIVE_SCHEDULE_DISPATCH_PAGE_PREFIX):
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "schedule dispatch page path is not available"},
                    )
                    return
                references = _parse_live_schedule_dispatch_page_path(parsed.path)
                if references is None:
                    self._write_json(
                        404,
                        {"error": "schedule dispatch page path is not available"},
                    )
                    return
                self._serve_live_schedule_dispatch_page(*references)
                return
            if parsed.path.startswith(_LIVE_RUN_DETAIL_PREFIX):
                run_id = parsed.path[len(_LIVE_RUN_DETAIL_PREFIX) :]
                if parsed.query or not _is_safe_live_run_id(run_id):
                    self._write_json(
                        404,
                        {"error": "run detail path is not available"},
                    )
                    return
                self._serve_live_run_detail(run_id)
                return
            if self.path == _LIVE_SNAPSHOT_PATH:
                self._serve_live_snapshot()
                return
            if self.path.startswith(_LIVE_SNAPSHOT_PATH + "?"):
                self._write_json(
                    404,
                    {"error": "live control snapshot path does not accept query parameters"},
                )
                return
            if self.path == _SERVICE_PROBE_PATH:
                self._serve_service_probe()
                return
            if self.path.startswith(_SERVICE_PROBE_PATH + "?"):
                self._write_json(
                    404,
                    {"error": "service probe path does not accept query parameters"},
                )
                return
            if self.path == _OPERATIONAL_READINESS_PATH:
                self._serve_operational_readiness()
                return
            if self.path.startswith(_OPERATIONAL_READINESS_PATH + "?"):
                self._write_json(
                    404,
                    {"error": "operational readiness path does not accept query parameters"},
                )
                return
            if self.path == _WORKFLOW_INVENTORY_PATH:
                self._serve_workflow_inventory()
                return
            if self.path.startswith(_WORKFLOW_INVENTORY_PATH + "?"):
                self._write_json(
                    404,
                    {"error": "workflow inventory path does not accept query parameters"},
                )
                return
            if parsed.path.startswith(_WORKFLOW_EXPLANATION_PREFIX):
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "workflow explanation path is not available"},
                    )
                    return
                references = _parse_live_workflow_explanation_path(parsed.path)
                if references is None:
                    self._write_json(
                        404,
                        {"error": "workflow explanation path is not available"},
                    )
                    return
                self._serve_workflow_explanation(*references)
                return
            if parsed.path.startswith(_WORKFLOW_DIFF_PREFIX):
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "workflow diff path is not available"},
                    )
                    return
                references = _parse_live_workflow_diff_path(parsed.path)
                if references is None:
                    self._write_json(
                        404,
                        {"error": "workflow diff path is not available"},
                    )
                    return
                self._serve_workflow_diff(*references)
                return
            if self.path == _SUPPORT_BUNDLE_PATH:
                self._serve_support_bundle()
                return
            if self.path.startswith(_SUPPORT_BUNDLE_PATH + "?"):
                self._write_json(
                    404,
                    {"error": "support bundle path does not accept query parameters"},
                )
                return
            super().do_GET()

        def do_POST(self):
            parsed = urlsplit(self.path)
            if parsed.path == _WORKFLOW_RELEASE_PREFLIGHT_PATH:
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "workflow release preflight path is not available"},
                    )
                    return
                self._serve_live_workflow_release_preflight()
                return
            if parsed.path == _WORKFLOW_RELEASE_PATH:
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "workflow publication path is not available"},
                    )
                    return
                self._serve_live_workflow_release()
                return
            if parsed.path == _WORKFLOW_PROMOTION_PATH:
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "workflow promotion path is not available"},
                    )
                    return
                self._serve_live_workflow_promotion()
                return
            if parsed.path == _WORKFLOW_DEPRECATION_PATH:
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "workflow deprecation path is not available"},
                    )
                    return
                self._serve_live_workflow_deprecation()
                return
            if parsed.path.startswith(_LIVE_SCHEDULE_DISPATCH_REVIEW_PREFIX):
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "schedule dispatch review path is not available"},
                    )
                    return
                dispatch_id = _parse_live_schedule_dispatch_review_path(parsed.path)
                if dispatch_id is None:
                    self._write_json(
                        404,
                        {"error": "schedule dispatch review path is not available"},
                    )
                    return
                self._serve_live_schedule_dispatch_review(dispatch_id)
                return
            if parsed.path.startswith(_WORKFLOW_PREFLIGHT_PREFIX):
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "workflow preflight path is not available"},
                    )
                    return
                references = _parse_live_workflow_preflight_path(parsed.path)
                if references is None:
                    self._write_json(
                        404,
                        {"error": "workflow preflight path is not available"},
                    )
                    return
                self._serve_workflow_preflight(*references)
                return
            if parsed.path.startswith(_LIVE_RESUME_PREFIX):
                if parsed.query:
                    self._write_json(
                        404,
                        {"error": "run action path is not available"},
                    )
                    return
                suffix = (
                    _LIVE_RESUME_SUFFIX
                    if parsed.path.endswith(_LIVE_RESUME_SUFFIX)
                    else _LIVE_CANCEL_SUFFIX
                    if parsed.path.endswith(_LIVE_CANCEL_SUFFIX)
                    else ""
                )
                if not suffix:
                    self._write_json(
                        404,
                        {"error": "run action path is not available"},
                    )
                    return
                run_id = parsed.path[len(_LIVE_RESUME_PREFIX) : -len(suffix)]
                if not _is_safe_live_run_id(run_id):
                    self._write_json(
                        404,
                        {"error": "run action path is not available"},
                    )
                    return
                if suffix == _LIVE_RESUME_SUFFIX:
                    self._serve_live_resume(run_id)
                else:
                    self._serve_live_cancel(run_id)
                return
            self.send_error(404)

        def _serve_live_snapshot(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "live control snapshot is not configured"})
                return
            try:
                snapshot = fetch_live_control_snapshot(
                    configured_service_url,
                    token_file,
                )
                body = json.dumps(
                    snapshot,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _LIVE_SNAPSHOT_MAX_RESPONSE_BYTES:
                    raise ValueError("live control snapshot unavailable")
            except Exception:
                self._write_json(503, {"error": "live control snapshot unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_service_probe(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            if configured_service_url is None:
                self._write_json(404, {"error": "service probe is not configured"})
                return
            try:
                probe = fetch_service_probe(configured_service_url)
                body = json.dumps(
                    probe,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _SERVICE_PROBE_MAX_RESPONSE_BYTES:
                    raise ValueError("service probe unavailable")
            except Exception:
                self._write_json(503, {"error": "service probe unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_operational_readiness(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "operational readiness is not configured"})
                return
            try:
                report = fetch_operational_readiness(configured_service_url, token_file)
                body = json.dumps(
                    report,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _OPERATIONAL_READINESS_MAX_RESPONSE_BYTES:
                    raise ValueError("operational readiness unavailable")
            except Exception:
                self._write_json(503, {"error": "operational readiness unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_workflow_inventory(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow inventory is not configured"})
                return
            try:
                inventory = fetch_workflow_inventory(configured_service_url, token_file)
                body = json.dumps(
                    inventory,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _WORKFLOW_INVENTORY_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow inventory unavailable")
            except Exception:
                self._write_json(503, {"error": "workflow inventory unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_workflow_explanation(self, workflow_id, version):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow explanation is not configured"})
                return
            try:
                explanation = fetch_workflow_explanation(
                    configured_service_url,
                    token_file,
                    workflow_id,
                    version,
                )
                body = json.dumps(
                    explanation,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _WORKFLOW_EXPLANATION_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow explanation unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "workflow version not found"})
                else:
                    self._write_json(503, {"error": "workflow explanation unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "workflow explanation unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_workflow_diff(self, workflow_id, from_version, to_version):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow diff is not configured"})
                return
            try:
                diff = fetch_workflow_diff(
                    configured_service_url,
                    token_file,
                    workflow_id,
                    from_version,
                    to_version,
                )
                body = json.dumps(
                    diff,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _WORKFLOW_DIFF_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow diff unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "workflow version not found"})
                else:
                    self._write_json(503, {"error": "workflow diff unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "workflow diff unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_workflow_preflight(self, workflow_id, version):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow preflight is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(
                    400,
                    {"error": "workflow preflight body must be an empty JSON object"},
                )
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(
                    400,
                    {"error": "workflow preflight body must be an empty JSON object"},
                )
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(
                    400,
                    {"error": "workflow preflight body must be an empty JSON object"},
                )
                return
            if content_length > _WORKFLOW_PREFLIGHT_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "workflow preflight body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(
                    400,
                    {"error": "workflow preflight body must be an empty JSON object"},
                )
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if payload != {}:
                self._write_json(
                    400,
                    {"error": "workflow preflight body must be an empty JSON object"},
                )
                return
            try:
                report = fetch_workflow_preflight(
                    configured_service_url,
                    token_file,
                    workflow_id,
                    version,
                    input_present=False,
                )
                response_body = json.dumps(
                    report,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(response_body) > _WORKFLOW_PREFLIGHT_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow preflight unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "workflow version not found"})
                else:
                    self._write_json(503, {"error": "workflow preflight unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "workflow preflight unavailable"})
                return
            self._write_json(200, response_body, content_type="application/json")

        def _serve_support_bundle(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "support bundle is not configured"})
                return
            try:
                bundle = fetch_support_bundle(configured_service_url, token_file)
                body = json.dumps(
                    bundle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _SUPPORT_BUNDLE_MAX_RESPONSE_BYTES:
                    raise ValueError("support bundle unavailable")
            except Exception:
                self._write_json(503, {"error": "support bundle unavailable"})
                return
            self._write_json(
                200,
                body,
                content_type="application/json",
                content_disposition='attachment; filename="skill2workflow-support-bundle.json"',
            )

        def _serve_live_run_detail(self, run_id):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "run detail is not configured"})
                return
            try:
                detail = fetch_run_detail(configured_service_url, token_file, run_id)
                body = json.dumps(
                    detail,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _LIVE_RUN_DETAIL_MAX_RESPONSE_BYTES:
                    raise ValueError("run detail unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "run not found"})
                else:
                    self._write_json(503, {"error": "run detail unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "run detail unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_live_run_page(self, cursor):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "run page is not configured"})
                return
            try:
                page = fetch_run_page(
                    configured_service_url,
                    token_file,
                    max_items=_LIVE_RUN_PAGE_MAX_ITEMS,
                    cursor=cursor,
                )
                body = json.dumps(
                    page,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _LIVE_RUN_PAGE_MAX_RESPONSE_BYTES:
                    raise ValueError("run page unavailable")
            except Exception:
                self._write_json(503, {"error": "run page unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_live_audit_page(self, cursor):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "audit page is not configured"})
                return
            try:
                page = fetch_audit_events(
                    configured_service_url,
                    token_file,
                    max_items=_LIVE_AUDIT_PAGE_MAX_ITEMS,
                    cursor=cursor,
                )
                body = json.dumps(
                    page,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _LIVE_AUDIT_PAGE_MAX_RESPONSE_BYTES:
                    raise ValueError("audit page unavailable")
            except Exception:
                self._write_json(503, {"error": "audit page unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_live_schedule_list(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "schedule list is not configured"})
                return
            try:
                page = fetch_recurring_schedule_list(
                    configured_service_url,
                    token_file,
                )
                body = json.dumps(
                    page,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _LIVE_SCHEDULE_LIST_MAX_RESPONSE_BYTES:
                    raise ValueError("schedule list unavailable")
            except Exception:
                self._write_json(503, {"error": "schedule list unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_live_schedule_dispatch_page(self, schedule_id, cursor):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "schedule dispatch page is not configured"})
                return
            try:
                page = fetch_recurring_schedule_dispatch_page(
                    configured_service_url,
                    token_file,
                    schedule_id=schedule_id,
                    max_items=_LIVE_SCHEDULE_DISPATCH_PAGE_MAX_ITEMS,
                    cursor=cursor,
                )
                body = json.dumps(
                    page,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(body) > _LIVE_SCHEDULE_DISPATCH_PAGE_MAX_RESPONSE_BYTES:
                    raise ValueError("schedule dispatch page unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "schedule not found"})
                else:
                    self._write_json(503, {"error": "schedule dispatch page unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "schedule dispatch page unavailable"})
                return
            self._write_json(200, body, content_type="application/json")

        def _serve_live_schedule_dispatch_review(self, dispatch_id):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "schedule dispatch review is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(
                    400,
                    {"error": "dispatch review body must contain expected timestamp and outcome"},
                )
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(
                    400,
                    {"error": "dispatch review body must contain expected timestamp and outcome"},
                )
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(
                    400,
                    {"error": "dispatch review body must contain expected timestamp and outcome"},
                )
                return
            if content_length > _LIVE_SCHEDULE_DISPATCH_REVIEW_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "dispatch review body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(
                    400,
                    {"error": "dispatch review body must contain expected timestamp and outcome"},
                )
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if (
                not isinstance(payload, dict)
                or set(payload) != {"expected_completed_at", "outcome"}
                or not isinstance(payload.get("expected_completed_at"), str)
                or not isinstance(payload.get("outcome"), str)
                or not payload.get("expected_completed_at")
                or len(payload["expected_completed_at"]) > 64
                or any(
                    ord(char) < 0x20 or ord(char) == 0x7F
                    for char in payload["expected_completed_at"]
                )
                or payload["outcome"] not in {
                    "effect_confirmed",
                    "effect_not_observed",
                    "no_conclusion",
                }
            ):
                self._write_json(
                    400,
                    {"error": "dispatch review body must contain expected timestamp and outcome"},
                )
                return
            try:
                review = post_recurring_schedule_dispatch_review(
                    configured_service_url,
                    token_file,
                    dispatch_id,
                    expected_completed_at=payload["expected_completed_at"],
                    outcome=payload["outcome"],
                )
                response_body = json.dumps(
                    review,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(response_body) > _LIVE_SCHEDULE_DISPATCH_REVIEW_MAX_RESPONSE_BYTES:
                    raise ValueError("dispatch review unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "dispatch review not found"})
                elif error.status_code == 409:
                    self._write_json(409, {"error": "dispatch review conflict"})
                else:
                    self._write_json(503, {"error": "dispatch review unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "dispatch review unavailable"})
                return
            self._write_json(200, response_body, content_type="application/json")

        def _serve_live_workflow_release_preflight(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow release preflight is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(400, {"error": "workflow release preflight body is malformed"})
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(400, {"error": "workflow release preflight body is malformed"})
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(400, {"error": "workflow release preflight body is malformed"})
                return
            if content_length > _WORKFLOW_RELEASE_PREFLIGHT_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "workflow release preflight body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(400, {"error": "workflow release preflight body is malformed"})
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if (
                not isinstance(payload, dict)
                or set(payload) != {"workflow"}
                or not isinstance(payload.get("workflow"), dict)
            ):
                self._write_json(400, {"error": "workflow release preflight body is malformed"})
                return
            try:
                response = post_workflow_release_preflight(
                    configured_service_url,
                    token_file,
                    payload["workflow"],
                )
                response_body = json.dumps(
                    response,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(response_body) > _WORKFLOW_RELEASE_PREFLIGHT_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow release preflight unavailable")
            except ServiceActionError as error:
                if error.status_code == 400:
                    self._write_json(400, {"error": "workflow release preflight rejected"})
                elif error.status_code == 413:
                    self._write_json(413, {"error": "workflow release preflight body is too large"})
                else:
                    self._write_json(503, {"error": "workflow release preflight unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "workflow release preflight unavailable"})
                return
            self._write_json(200, response_body, content_type="application/json")

        def _serve_live_workflow_release(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow publication is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(400, {"error": "workflow publication body is malformed"})
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(400, {"error": "workflow publication body is malformed"})
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(400, {"error": "workflow publication body is malformed"})
                return
            if content_length > _WORKFLOW_RELEASE_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "workflow publication body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(400, {"error": "workflow publication body is malformed"})
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if (
                not isinstance(payload, dict)
                or set(payload) != {"workflow"}
                or not isinstance(payload.get("workflow"), dict)
            ):
                self._write_json(400, {"error": "workflow publication body is malformed"})
                return
            try:
                response = post_workflow_release(
                    configured_service_url,
                    token_file,
                    payload["workflow"],
                )
                response_body = json.dumps(
                    response,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(response_body) > _WORKFLOW_RELEASE_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow publication unavailable")
            except ServiceActionError as error:
                if error.status_code == 400:
                    self._write_json(400, {"error": "workflow publication rejected"})
                elif error.status_code == 409:
                    self._write_json(409, {"error": "workflow version is immutable"})
                elif error.status_code == 413:
                    self._write_json(413, {"error": "workflow publication body is too large"})
                else:
                    self._write_json(503, {"error": "workflow publication unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "workflow publication unavailable"})
                return
            self._write_json(200, response_body, content_type="application/json")

        def _serve_live_workflow_promotion(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow promotion is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(400, {"error": "workflow promotion body is malformed"})
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(400, {"error": "workflow promotion body is malformed"})
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(400, {"error": "workflow promotion body is malformed"})
                return
            if content_length > _WORKFLOW_PROMOTION_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "workflow promotion body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(400, {"error": "workflow promotion body is malformed"})
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if (
                not isinstance(payload, dict)
                or set(payload) != {
                    "workflow_id",
                    "version",
                    "alias",
                    "expected_current_version",
                }
                or any(not isinstance(payload.get(field), str) for field in payload)
                or payload.get("alias") != "production"
                or not _is_safe_workflow_ref(payload.get("workflow_id"), allow_empty=False)
                or not _is_safe_workflow_ref(payload.get("version"), allow_empty=False)
                or not _is_safe_workflow_ref(payload.get("expected_current_version"), allow_empty=True)
            ):
                self._write_json(400, {"error": "workflow promotion body is malformed"})
                return
            try:
                response = post_workflow_promotion(
                    configured_service_url,
                    token_file,
                    payload["workflow_id"],
                    payload["version"],
                    alias="production",
                    expected_current_version=payload["expected_current_version"],
                )
                response_body = json.dumps(
                    response,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(response_body) > _WORKFLOW_PROMOTION_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow promotion unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "workflow version not found"})
                elif error.status_code == 409:
                    self._write_json(409, {"error": "workflow promotion conflict"})
                else:
                    self._write_json(503, {"error": "workflow promotion unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "workflow promotion unavailable"})
                return
            self._write_json(200, response_body, content_type="application/json")

        def _serve_live_workflow_deprecation(self):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "workflow deprecation is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(400, {"error": "workflow deprecation body is malformed"})
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(400, {"error": "workflow deprecation body is malformed"})
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(400, {"error": "workflow deprecation body is malformed"})
                return
            if content_length > _WORKFLOW_DEPRECATION_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "workflow deprecation body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(400, {"error": "workflow deprecation body is malformed"})
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if (
                not isinstance(payload, dict)
                or set(payload)
                != {"workflow_id", "version", "expected_checksum", "expected_aliases"}
                or not _is_safe_workflow_ref(payload.get("workflow_id"), allow_empty=False)
                or not _is_safe_workflow_ref(payload.get("version"), allow_empty=False)
                or not isinstance(payload.get("expected_checksum"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", payload.get("expected_checksum", ""))
                or not isinstance(payload.get("expected_aliases"), list)
                or len(payload["expected_aliases"]) > 16
                or any(
                    not isinstance(alias, str)
                    or not _WORKFLOW_ALIAS_PATTERN.fullmatch(alias)
                    for alias in payload["expected_aliases"]
                )
                or len(set(payload["expected_aliases"]))
                != len(payload["expected_aliases"])
            ):
                self._write_json(400, {"error": "workflow deprecation body is malformed"})
                return
            try:
                response = post_workflow_deprecation(
                    configured_service_url,
                    token_file,
                    payload["workflow_id"],
                    payload["version"],
                    expected_checksum=payload["expected_checksum"],
                    expected_aliases=payload["expected_aliases"],
                )
                response_body = json.dumps(
                    response,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(response_body) > _WORKFLOW_DEPRECATION_MAX_RESPONSE_BYTES:
                    raise ValueError("workflow deprecation unavailable")
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "workflow version not found"})
                elif error.status_code == 409:
                    self._write_json(409, {"error": "workflow deprecation conflict"})
                else:
                    self._write_json(503, {"error": "workflow deprecation unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "workflow deprecation unavailable"})
                return
            self._write_json(200, response_body, content_type="application/json")

        def _serve_live_resume(self, run_id):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "human gate is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(
                    400,
                    {"error": "human gate decision body must contain approved boolean"},
                )
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(
                    400,
                    {"error": "human gate decision body must contain approved boolean"},
                )
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(
                    400,
                    {"error": "human gate decision body must contain approved boolean"},
                )
                return
            if content_length > _LIVE_RESUME_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "human gate decision body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(
                    400,
                    {"error": "human gate decision body must contain approved boolean"},
                )
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if (
                not isinstance(payload, dict)
                or set(payload) != {"approved"}
                or not isinstance(payload.get("approved"), bool)
            ):
                self._write_json(
                    400,
                    {"error": "human gate decision body must contain approved boolean"},
                )
                return
            try:
                result = post_run_resume(
                    configured_service_url,
                    token_file,
                    run_id,
                    approved=payload["approved"],
                )
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "run not found"})
                elif error.status_code == 409:
                    self._write_json(409, {"error": "run is not waiting"})
                else:
                    self._write_json(503, {"error": "human gate decision unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "human gate decision unavailable"})
                return
            self._write_json(200, result)

        def _serve_live_cancel(self, run_id):
            configured_service_url = getattr(self.server, "live_service_url", None)
            token_file = getattr(self.server, "live_auth_token_file", None)
            if configured_service_url is None or token_file is None:
                self._write_json(404, {"error": "run cancellation is not configured"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._write_json(
                    400,
                    {"error": "run cancellation body must be an empty JSON object"},
                )
                return
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1:
                self._write_json(
                    400,
                    {"error": "run cancellation body must be an empty JSON object"},
                )
                return
            try:
                content_length = int(content_lengths[0])
            except (TypeError, ValueError):
                content_length = -1
            if content_length < 0:
                self._write_json(
                    400,
                    {"error": "run cancellation body must be an empty JSON object"},
                )
                return
            if content_length > _LIVE_CANCEL_MAX_REQUEST_BYTES:
                self._write_json(413, {"error": "run cancellation body is too large"})
                return
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_json(
                    400,
                    {"error": "run cancellation body must be an empty JSON object"},
                )
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if payload != {}:
                self._write_json(
                    400,
                    {"error": "run cancellation body must be an empty JSON object"},
                )
                return
            try:
                result = post_run_cancel(configured_service_url, token_file, run_id)
            except ServiceActionError as error:
                if error.status_code == 404:
                    self._write_json(404, {"error": "run not found"})
                elif error.status_code == 409:
                    self._write_json(409, {"error": "run cannot be cancelled"})
                else:
                    self._write_json(503, {"error": "run cancellation unavailable"})
                return
            except Exception:
                self._write_json(503, {"error": "run cancellation unavailable"})
                return
            self._write_json(200, result)

        def _write_json(
            self,
            status,
            payload,
            *,
            content_type="application/json",
            content_disposition=None,
        ):
            if isinstance(payload, dict):
                body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            else:
                body = bytes(payload)
            self.send_response(int(status))
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if content_disposition:
                self.send_header("Content-Disposition", content_disposition)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    handler = partial(QuietHandler, directory=str(root))
    server_class = HTTPServer if once else ThreadingHTTPServer
    server = server_class((host, int(port)), handler)
    server.live_service_url = service_url
    server.live_auth_token_file = Path(auth_token_file) if auth_token_file else None
    try:
        if ready_callback:
            ready_callback(server)
        if once:
            server.handle_request()
        else:
            server.serve_forever()
    finally:
        server.server_close()


def _is_safe_live_run_id(value: str) -> bool:
    """Accept only the ASCII run identifiers used by the fixed live route."""

    return bool(
        value.startswith("run_")
        and 5 <= len(value) <= 128
        and all(char.isascii() and (char.isalnum() or char in {"_", "-"}) for char in value)
    )


def _parse_live_workflow_explanation_path(path: str):
    """Accept exactly two safe, encoded Workflow reference components."""

    return _parse_live_workflow_reference_path(path, _WORKFLOW_EXPLANATION_PREFIX)


def _parse_live_schedule_dispatch_page_path(path: str):
    """Accept a schedule id and optional fixed-safe dispatch cursor."""

    if not path.startswith(_LIVE_SCHEDULE_DISPATCH_PAGE_PREFIX):
        return None
    suffix = path[len(_LIVE_SCHEDULE_DISPATCH_PAGE_PREFIX) :]
    parts = suffix.split("/")
    if len(parts) not in {1, 2} or any(not part for part in parts):
        return None
    values = tuple(unquote(part) for part in parts)
    schedule_id = values[0]
    if (
        not schedule_id
        or len(schedule_id) > 128
        or not all(char.isalnum() or char in {"-", "_", "."} for char in schedule_id)
    ):
        return None
    cursor = values[1] if len(values) == 2 else ""
    if cursor and (
        len(cursor) > 512
        or not all(
            char in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for char in cursor
        )
    ):
        return None
    return schedule_id, cursor


def _parse_live_schedule_dispatch_review_path(path: str):
    """Accept exactly one safe dispatch id for the protected review action."""

    if not path.startswith(_LIVE_SCHEDULE_DISPATCH_REVIEW_PREFIX):
        return None
    suffix = path[len(_LIVE_SCHEDULE_DISPATCH_REVIEW_PREFIX) :]
    if not suffix or "/" in suffix:
        return None
    dispatch_id = unquote(suffix)
    if (
        not dispatch_id
        or len(dispatch_id) > 128
        or not all(char.isalnum() or char in {"-", "_", "."} for char in dispatch_id)
    ):
        return None
    return dispatch_id


def _is_safe_workflow_ref(value, *, allow_empty):
    """Match the service workflow-reference boundary for fixed UI bodies."""

    if not isinstance(value, str) or len(value) > 128:
        return False
    if not allow_empty and not value:
        return False
    return not any(
        ord(char) < 0x20 or ord(char) == 0x7F or char in {"/", "?", "#"}
        for char in value
    )


def _parse_live_workflow_preflight_path(path: str):
    """Accept exactly two safe, encoded Workflow references for preflight."""

    return _parse_live_workflow_reference_path(path, _WORKFLOW_PREFLIGHT_PREFIX)


def _parse_live_workflow_diff_path(path: str):
    """Accept exactly three safe, encoded Workflow diff references."""

    return _parse_live_workflow_reference_path(
        path,
        _WORKFLOW_DIFF_PREFIX,
        component_count=3,
    )


def _parse_live_workflow_reference_path(path: str, prefix: str, *, component_count: int = 2):
    if not path.startswith(prefix):
        return None
    suffix = path[len(prefix) :]
    parts = suffix.split("/")
    if len(parts) != component_count or any(not part for part in parts):
        return None
    values = tuple(unquote(part) for part in parts)
    if any(
        not value
        or len(value) > 128
        or any(
            ord(char) < 0x20
            or ord(char) == 0x7F
            or char in {"/", "?", "#"}
            for char in value
        )
        for value in values
    ):
        return None
    return values


def _parse_live_run_page_cursor(query: str) -> str:
    """Accept only one opaque cursor for the fixed live run-page proxy."""

    if not query:
        return ""
    try:
        values = parse_qs(query, keep_blank_values=True, strict_parsing=True)
    except ValueError as error:
        raise ValueError("run page query is invalid") from error
    if set(values) != {"cursor"} or len(values["cursor"]) != 1:
        raise ValueError("run page query is invalid")
    cursor = values["cursor"][0]
    if (
        not cursor
        or len(cursor) > 128
        or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for char in cursor)
    ):
        raise ValueError("run page cursor is invalid")
    return cursor


def _parse_live_audit_page_cursor(query: str) -> str:
    """Accept only one opaque cursor for the fixed live audit-page proxy."""

    if not query:
        return ""
    try:
        values = parse_qs(query, keep_blank_values=True, strict_parsing=True)
    except ValueError as error:
        raise ValueError("audit page query is invalid") from error
    if set(values) != {"cursor"} or len(values["cursor"]) != 1:
        raise ValueError("audit page query is invalid")
    cursor = values["cursor"][0]
    if (
        not cursor
        or len(cursor) > 128
        or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for char in cursor)
    ):
        raise ValueError("audit page cursor is invalid")
    return cursor
