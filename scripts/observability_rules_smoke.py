#!/usr/bin/env python3
"""Check the committed Prometheus alert starter pack without runtime dependencies."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "examples" / "observability" / "prometheus-alerts.yml"

EXPECTED_ALERTS = (
    "Skill2WorkflowServiceNotReady",
    "Skill2WorkflowSchedulerLeaseLost",
    "Skill2WorkflowUncertainDispatch",
    "Skill2WorkflowBusinessRequestSaturation",
    "Skill2WorkflowHttp5xxResponses",
)
FIXED_METRICS = (
    "skill2workflow_service_ready",
    "skill2workflow_scheduler_lease_owned",
    "skill2workflow_schedule_dispatches",
    "skill2workflow_service_inflight_requests",
    "skill2workflow_http_requests_total",
)
FORBIDDEN_MARKERS = (
    "Authorization",
    "Bearer ",
    "secret",
    "token",
    "customer",
    "run_id",
)


def main() -> int:
    text = RULES.read_text(encoding="utf-8")
    checks = {
        "rule_file_exists": RULES.is_file(),
        "group_declared": "name: skill2workflow.service" in text,
        "expected_alerts_present": all(
            f"alert: {alert}" in text for alert in EXPECTED_ALERTS
        ),
        "fixed_metrics_only": all(metric in text for metric in FIXED_METRICS),
        "no_user_controlled_label_interpolation": "$" not in text,
        "no_sensitive_markers": not any(
            marker.lower() in text.lower() for marker in FORBIDDEN_MARKERS
        ),
        "bounded_rule_count": text.count("- alert:") == len(EXPECTED_ALERTS),
        "bounded_annotations": all(
            len(line.strip()) <= 240
            for line in text.splitlines()
            if line.strip().startswith(("summary:", "description:"))
        ),
    }
    evidence = {
        "schema_version": "skill2workflow-observability-rules-evidence-0.1.0",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "alert_count": text.count("- alert:"),
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
