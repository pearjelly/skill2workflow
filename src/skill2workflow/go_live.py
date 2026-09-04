"""Read-only single-instance deployment gate composed from existing controls."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .lark_tenant_credential_check import check_lark_tenant_credential
from .service_client import fetch_operational_readiness, fetch_service_probe
from .service_doctor import diagnose_service


GO_LIVE_CHECK_SCHEMA_VERSION = "skill2workflow-go-live-check-0.1.0"


def assess_go_live(
    config_path: Path,
    service_url: str,
    auth_token_file: Path,
    *,
    verify_lark_tenant_credential: bool = False,
) -> Dict[str, object]:
    """Compose local and remote readiness without mutation or error disclosure.

    The token-bearing operational read is deliberately skipped unless local
    Doctor checks and the unauthenticated probe have already reported ready.
    An approved Feishu China credential can be checked only when the caller
    explicitly opts in; it runs after the local Doctor and before any service
    or ingress-token access.
    """

    doctor = diagnose_service(config_path, check_bind=False)
    local = {
        "status": doctor["status"],
        "check_count": len(doctor["checks"]),
        "failed_check_ids": [
            check["id"]
            for check in doctor["checks"]
            if check["status"] == "failed"
        ],
        "skipped_check_ids": [
            check["id"]
            for check in doctor["checks"]
            if check["status"] == "skipped"
        ],
    }
    if doctor["status"] != "ready":
        return _result(
            "not_ready",
            local,
            _probe_not_checked(),
            _operational_not_checked(),
            lark_tenant_credential=(
                _lark_tenant_credential_not_checked("blocked_by_local_doctor")
                if verify_lark_tenant_credential
                else None
            ),
        )

    lark_tenant_credential = None
    if verify_lark_tenant_credential:
        lark_tenant_credential = _summarize_lark_tenant_credential(
            check_lark_tenant_credential(config_path)
        )
        if lark_tenant_credential["status"] != "ready":
            return _result(
                "not_ready",
                local,
                _probe_not_checked(),
                _operational_not_checked(),
                lark_tenant_credential=lark_tenant_credential,
            )

    try:
        probe = fetch_service_probe(service_url)
    except Exception:
        return _result(
            "unavailable",
            local,
            _probe_unavailable(),
            _operational_not_checked(),
            lark_tenant_credential=lark_tenant_credential,
        )

    probe_summary = {
        "status": probe["status"],
        "health": probe["health"]["status"],
        "readiness": probe["readiness"]["status"],
    }
    if probe["status"] != "ready":
        return _result(
            "not_ready",
            local,
            probe_summary,
            _operational_not_checked(),
            lark_tenant_credential=lark_tenant_credential,
        )

    try:
        operational = fetch_operational_readiness(service_url, auth_token_file)
    except Exception:
        return _result(
            "unavailable",
            local,
            probe_summary,
            _operational_unavailable(),
            lark_tenant_credential=lark_tenant_credential,
        )

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
        lark_tenant_credential=lark_tenant_credential,
    )


def _result(status, local, probe, operational, *, lark_tenant_credential=None):
    result = {
        "schema_version": GO_LIVE_CHECK_SCHEMA_VERSION,
        "status": status,
        "local_doctor": local,
        "service_probe": probe,
        "operational_readiness": operational,
    }
    if lark_tenant_credential is not None:
        result["lark_tenant_credential"] = lark_tenant_credential
    return result


def _lark_tenant_credential_not_checked(reason):
    return {
        "status": "not_checked",
        "provider": "lark_tenant_access_token",
        "reason": reason,
    }


def _summarize_lark_tenant_credential(result):
    """Keep the opt-in provider result fixed and value-free at this boundary."""

    if not isinstance(result, dict):
        return {
            "status": "not_ready",
            "provider": "lark_tenant_access_token",
            "reason": "credential_unavailable",
        }
    status = result.get("status")
    reason = result.get("reason")
    if status not in {"ready", "not_ready"} or reason not in {
        "validated",
        "invalid_config",
        "not_configured",
        "credential_unavailable",
    }:
        return {
            "status": "not_ready",
            "provider": "lark_tenant_access_token",
            "reason": "credential_unavailable",
        }
    return {
        "status": status,
        "provider": "lark_tenant_access_token",
        "reason": reason,
    }


def _probe_not_checked():
    return {"status": "not_checked", "health": "not_checked", "readiness": "not_checked"}


def _probe_unavailable():
    return {"status": "unavailable", "health": "unavailable", "readiness": "unavailable"}


def _operational_not_checked():
    return {"status": "not_checked", "blocking_reasons": [], "operator_notes": []}


def _operational_unavailable():
    return {"status": "unavailable", "blocking_reasons": [], "operator_notes": []}
