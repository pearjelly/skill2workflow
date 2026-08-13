#!/usr/bin/env python3
"""Check the committed Grafana dashboard against fixed service metrics."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "examples" / "observability" / "grafana-dashboard.json"
EXPECTED_METRICS = (
    "skill2workflow_service_ready",
    "skill2workflow_scheduler_lease_owned",
    "skill2workflow_service_inflight_requests",
    "skill2workflow_schedule_dispatches",
    "skill2workflow_http_requests_total",
    "skill2workflow_runs",
    "skill2workflow_service_uptime_seconds",
)
ALLOWED_LABELS = ("status", "status_class")
FORBIDDEN_MARKERS = (
    "Authorization",
    "Bearer ",
    "secret",
    "token",
    "customer",
    "run_id",
    "workflow_id",
)


def main() -> int:
    raw = DASHBOARD.read_text(encoding="utf-8")
    dashboard = json.loads(raw)
    panels = dashboard.get("panels") if isinstance(dashboard, dict) else None
    expressions = [
        target.get("expr", "")
        for panel in panels or []
        for target in panel.get("targets", [])
        if isinstance(panel, dict) and isinstance(target, dict)
    ]
    expression_text = "\n".join(expressions)
    panel_ids = [panel.get("id") for panel in panels or [] if isinstance(panel, dict)]
    input_names = [
        item.get("name")
        for item in dashboard.get("__inputs", [])
        if isinstance(item, dict)
    ]
    all_text = raw.lower()
    checks = {
        "dashboard_file_exists": DASHBOARD.is_file(),
        "dashboard_identity_is_fixed": (
            dashboard.get("uid") == "skill2workflow-service"
            and dashboard.get("schemaVersion") == 39
        ),
        "prometheus_input_declared": input_names == ["DS_PROMETHEUS"],
        "bounded_panel_set": len(panels or []) == 8,
        "unique_panel_ids": len(panel_ids) == len(set(panel_ids)),
        "supported_panel_types": all(
            panel.get("type") in {"stat", "timeseries"}
            for panel in panels or []
            if isinstance(panel, dict)
        ),
        "fixed_metrics_present": all(metric in expression_text for metric in EXPECTED_METRICS),
        "fixed_labels_only": all(
            label in expression_text for label in ALLOWED_LABELS
        )
        and not any(
            marker in expression_text
            for marker in ("instance", "job", "pod", "namespace", "tenant")
        ),
        "no_user_interpolation_in_expressions": "$" not in expression_text,
        "no_sensitive_markers": not any(
            marker.lower() in all_text for marker in FORBIDDEN_MARKERS
        ),
    }
    evidence = {
        "schema_version": "skill2workflow-observability-dashboard-evidence-0.1.0",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "panel_count": len(panels or []),
        "expression_count": len(expressions),
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
