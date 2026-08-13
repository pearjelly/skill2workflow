"""Low-cardinality service metrics and allowlisted operational events."""

from __future__ import annotations

import json
import math
import sqlite3
import sys
import threading
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional, TextIO


TELEMETRY_EVENT_SCHEMA_VERSION = "skill2workflow-operational-event-0.1.0"
_SERVICE = "skill2workflow"
_ROUTES = (
    "health",
    "readiness",
    "metrics",
    "control_snapshot",
    "recurring_schedule_list",
    "recurring_schedule_action",
    "audit_consistency",
    "support_bundle",
    "run_list",
    "run_detail",
    "workflow_trigger",
    "run_cancel",
    "run_resume",
    "unknown",
)
_STATUS_CLASSES = ("2xx", "4xx", "5xx")
_WORKFLOW_STATUSES = ("published", "deprecated", "other")
_RUN_STATUSES = (
    "created",
    "running",
    "waiting",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
    "other",
)
_DISPATCH_STATUSES = ("claimed", "completed", "failed", "skipped", "uncertain", "other")
_LIFECYCLE_STATUSES = {"starting", "ready", "draining", "stopped"}
_METHODS = {"GET", "POST", "PUT", "DELETE"}


class RuntimeTelemetry:
    """Render aggregate runtime state in Prometheus text exposition format."""

    def __init__(self, state_dir: Path, monotonic: Callable[[], float] = time.monotonic):
        self.state_dir = Path(state_dir)
        self._monotonic = monotonic
        self._started_at = monotonic()
        self._http_counts = Counter()
        self._lock = threading.Lock()

    def observe_http(self, route: str, status_code: int) -> None:
        normalized_route = route if route in _ROUTES else "unknown"
        status_class = _status_class(status_code)
        with self._lock:
            self._http_counts[(normalized_route, status_class)] += 1

    def aggregate(self, *, service_status: str, ready: bool, scheduler_lease_owned: bool) -> Dict[str, object]:
        """Return the same fixed, value-free aggregates used by metrics export."""

        workflow_counts = self._grouped_counts(
            "control.sqlite3", "workflow_versions", "status", _WORKFLOW_STATUSES
        )
        run_counts = self._grouped_counts("runs.sqlite3", "runs", "status", _RUN_STATUSES)
        dispatch_counts = self._grouped_counts(
            "scheduler.sqlite3", "schedule_dispatches", "status", _DISPATCH_STATUSES
        )
        audit_count = self._table_count("control.sqlite3", "audit_events")
        schedule_count = self._table_count("scheduler.sqlite3", "recurring_schedules")
        with self._lock:
            http_counts = dict(self._http_counts)

        lifecycle = service_status if service_status in _LIFECYCLE_STATUSES else "unknown"
        http_requests = {
            route: {
                status_class: int(http_counts.get((route, status_class), 0))
                for status_class in _STATUS_CLASSES
            }
            for route in _ROUTES
        }
        return {
            "service_status": lifecycle,
            "ready": bool(ready),
            "scheduler_lease_owned": bool(scheduler_lease_owned),
            "uptime_seconds": round(
                max(0.0, float(self._monotonic()) - float(self._started_at)), 3
            ),
            "workflow_status_counts": workflow_counts,
            "run_status_counts": run_counts,
            "dispatch_status_counts": dispatch_counts,
            "audit_event_count": audit_count,
            "recurring_schedule_count": schedule_count,
            "http_requests": http_requests,
        }

    def render(self, *, service_status: str, ready: bool, scheduler_lease_owned: bool) -> str:
        aggregate = self.aggregate(
            service_status=service_status,
            ready=ready,
            scheduler_lease_owned=scheduler_lease_owned,
        )
        workflow_counts = aggregate["workflow_status_counts"]
        run_counts = aggregate["run_status_counts"]
        dispatch_counts = aggregate["dispatch_status_counts"]
        audit_count = aggregate["audit_event_count"]
        schedule_count = aggregate["recurring_schedule_count"]
        uptime = aggregate["uptime_seconds"]
        lifecycle = aggregate["service_status"]
        http_requests = aggregate["http_requests"]
        lines = [
            "# HELP skill2workflow_service_ready Whether the service is ready to accept workflow traffic.",
            "# TYPE skill2workflow_service_ready gauge",
            f"skill2workflow_service_ready {int(bool(ready))}",
            "# HELP skill2workflow_scheduler_lease_owned Whether this process owns the scheduler lease.",
            "# TYPE skill2workflow_scheduler_lease_owned gauge",
            f"skill2workflow_scheduler_lease_owned {int(bool(scheduler_lease_owned))}",
            "# HELP skill2workflow_service_uptime_seconds Monotonic process uptime in seconds.",
            "# TYPE skill2workflow_service_uptime_seconds gauge",
            f"skill2workflow_service_uptime_seconds {uptime:.3f}",
            "# HELP skill2workflow_service_state Current service lifecycle state.",
            "# TYPE skill2workflow_service_state gauge",
        ]
        for status in ("starting", "ready", "draining", "stopped", "unknown"):
            lines.append(f'skill2workflow_service_state{{status="{status}"}} {int(status == lifecycle)}')
        lines.extend(self._status_metric("skill2workflow_workflows", workflow_counts))
        lines.extend(self._status_metric("skill2workflow_runs", run_counts))
        lines.extend(
            [
                "# HELP skill2workflow_audit_events Persisted audit event count.",
                "# TYPE skill2workflow_audit_events gauge",
                f"skill2workflow_audit_events {audit_count}",
                "# HELP skill2workflow_recurring_schedules Persisted recurring schedule count.",
                "# TYPE skill2workflow_recurring_schedules gauge",
                f"skill2workflow_recurring_schedules {schedule_count}",
            ]
        )
        lines.extend(self._status_metric("skill2workflow_schedule_dispatches", dispatch_counts))
        lines.extend(
            [
                "# HELP skill2workflow_http_requests_total HTTP requests by fixed route and status class.",
                "# TYPE skill2workflow_http_requests_total counter",
            ]
        )
        for route in _ROUTES:
            for status_class in _STATUS_CLASSES:
                lines.append(
                    "skill2workflow_http_requests_total"
                    f'{{route="{route}",status_class="{status_class}"}} '
                    f"{http_requests[route][status_class]}"
                )
        return "\n".join(lines) + "\n"

    def _table_count(self, database: str, table: str) -> int:
        with self._connection(database) as connection:
            row = connection.execute(f"select count(*) from {table}").fetchone()
        return int(row[0])

    def _grouped_counts(self, database: str, table: str, column: str, statuses):
        counts = {status: 0 for status in statuses}
        with self._connection(database) as connection:
            rows = connection.execute(
                f"select {column}, count(*) from {table} group by {column}"
            ).fetchall()
        for value, count in rows:
            candidate = str(value)
            normalized = candidate if candidate in counts and candidate != "other" else "other"
            counts[normalized] += int(count)
        return counts

    def _connection(self, database: str):
        path = (self.state_dir / database).resolve()
        return closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True))

    @staticmethod
    def _status_metric(name: str, counts):
        help_text = name.removeprefix("skill2workflow_").replace("_", " ").capitalize()
        lines = [f"# HELP {name} {help_text} by fixed status.", f"# TYPE {name} gauge"]
        lines.extend(f'{name}{{status="{status}"}} {count}' for status, count in counts.items())
        return lines


class OperationalEventLogger:
    """Write only fixed-shape, non-user-controlled operational NDJSON events."""

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.stream = stream if stream is not None else sys.stdout
        self._now = now
        self._lock = threading.Lock()

    def lifecycle(self, status: str) -> None:
        normalized = status if status in _LIFECYCLE_STATUSES else "unknown"
        self._write(
            {
                "schema_version": TELEMETRY_EVENT_SCHEMA_VERSION,
                "timestamp": self._timestamp(),
                "event_type": "service_lifecycle",
                "service": _SERVICE,
                "status": normalized,
            }
        )

    def request_completed(
        self, *, method: str, route: str, status_code: int, duration_ms: float
    ) -> None:
        normalized_method = method if method in _METHODS else "OTHER"
        normalized_route = route if route in _ROUTES else "unknown"
        normalized_status = (
            status_code
            if isinstance(status_code, int) and not isinstance(status_code, bool) and 100 <= status_code <= 599
            else 500
        )
        duration = float(duration_ms)
        normalized_duration = max(0, round(duration)) if math.isfinite(duration) else 0
        self._write(
            {
                "schema_version": TELEMETRY_EVENT_SCHEMA_VERSION,
                "timestamp": self._timestamp(),
                "event_type": "http_request_completed",
                "service": _SERVICE,
                "method": normalized_method,
                "route": normalized_route,
                "status_code": normalized_status,
                "status_class": _status_class(normalized_status),
                "duration_ms": normalized_duration,
            }
        )

    def _timestamp(self) -> str:
        value = self._now()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()

    def _write(self, event) -> None:
        line = json.dumps(event, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        with self._lock:
            self.stream.write(line + "\n")
            self.stream.flush()


def _status_class(status_code: int) -> str:
    try:
        value = int(status_code)
    except (TypeError, ValueError):
        return "5xx"
    if 200 <= value <= 299:
        return "2xx"
    if 400 <= value <= 499:
        return "4xx"
    return "5xx"
