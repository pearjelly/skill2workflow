"""Read-only single-instance deployment gate composed from existing controls."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .service_client import fetch_operational_readiness, fetch_service_probe
from .service_doctor import diagnose_service


GO_LIVE_CHECK_SCHEMA_VERSION = "skill2workflow-go-live-check-0.1.0"


def assess_go_live(
    config_path: Path,
    service_url: str,
    auth_token_file: Path,
) -> Dict[str, object]:
    """Compose local and remote readiness without mutation or error disclosure.

    The token-bearing operational read is deliberately skipped unless local
    Doctor checks and the unauthenticated probe have already reported ready.
    """

    doctor = diagnose_service(config_path)
    local = {
        "status": doctor["status"],
        "check_count": len(doctor["checks"]),
        "failed_check_ids": [
            check["id"]
            for check in doctor["checks"]
            if check["status"] != "passed"
        ],
    }
    if doctor["status"] != "ready":
        return _result("not_ready", local, _probe_not_checked(), _operational_not_checked())

    try:
        probe = fetch_service_probe(service_url)
    except Exception:
        return _result("unavailable", local, _probe_unavailable(), _operational_not_checked())

    probe_summary = {
        "status": probe["status"],
        "health": probe["health"]["status"],
        "readiness": probe["readiness"]["status"],
    }
    if probe["status"] != "ready":
        return _result("not_ready", local, probe_summary, _operational_not_checked())

    try:
        operational = fetch_operational_readiness(service_url, auth_token_file)
    except Exception:
        return _result("unavailable", local, probe_summary, _operational_unavailable())

    operational_summary = {
        "status": operational["status"],
        "blocking_reasons": list(operational["blocking_reasons"]),
        "operator_notes": list(operational["operator_notes"]),
    }
    return _result(
        "ready" if operational["status"] == "ready" else "not_ready",
        local,
        probe_summary,
        operational_summary,
    )


def _result(status, local, probe, operational):
    return {
        "schema_version": GO_LIVE_CHECK_SCHEMA_VERSION,
        "status": status,
        "local_doctor": local,
        "service_probe": probe,
        "operational_readiness": operational,
    }


def _probe_not_checked():
    return {"status": "not_checked", "health": "not_checked", "readiness": "not_checked"}


def _probe_unavailable():
    return {"status": "unavailable", "health": "unavailable", "readiness": "unavailable"}


def _operational_not_checked():
    return {"status": "not_checked", "blocking_reasons": [], "operator_notes": []}


def _operational_unavailable():
    return {"status": "unavailable", "blocking_reasons": [], "operator_notes": []}
