"""Guarded one-shot validation for the scoped live Lark task connector."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict

from .connectors import ConnectorRuntime, ExternalConnector
from .credentials import StaticCredentialProvider
from .external_connectors import load_external_connector


LIVE_SWITCH = "SKILL2WORKFLOW_LARK_TASK_LIVE"
TOKEN_ENVIRONMENT = "LARK_BOT_ACCESS_TOKEN"


def run_lark_task_live_validation(
    repo_root: Path,
    title: str,
    description: str,
    assignee_open_id: str,
    validation_run_id: str,
    confirmed: bool,
    transport=None,
) -> Dict[str, object]:
    if not confirmed:
        raise ValueError("live validation requires --confirm-live-create")
    if os.environ.get(LIVE_SWITCH) != "1":
        raise ValueError("SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required")
    token = os.environ.get(TOKEN_ENVIRONMENT, "")
    if not token:
        raise ValueError("LARK_BOT_ACCESS_TOKEN is required")
    if not validation_run_id:
        raise ValueError("validation run id is required")
    if not assignee_open_id:
        raise ValueError("assignee open id is required")

    connector = load_external_connector(Path(repo_root) / "examples" / "connectors" / "lark_task_connector.py")
    if transport is not None:
        original = connector

        def execute_with_transport(binding, credential_provider=None, context=None):
            return original.executor(
                binding,
                credential_provider=credential_provider,
                context=context,
                transport=transport,
            )

        connector = ExternalConnector(manifest=original.manifest, executor=execute_with_transport)

    runtime = ConnectorRuntime([connector])
    result = runtime.execute_connector(
        _validation_node(title, description, assignee_open_id),
        credential_provider=StaticCredentialProvider({"lark_bot_access_token": token}),
        context={
            "_execution": {
                "workflow_id": "workflow_lark_task_live_validation",
                "workflow_version": "0.1.0",
                "run_id": validation_run_id,
                "node_id": "create_lark_task",
            }
        },
    )
    audit = result.get("audit", {}) if isinstance(result.get("audit"), dict) else {}
    return {
        "ok": result.get("status") == "completed",
        "connector_id": str(result.get("connector", {}).get("id", "")),
        "operation": str(audit.get("operation", "")),
        "mode": str(audit.get("mode", "")),
        "credential_status": str(audit.get("credential_status", "")),
        "idempotency_key_present": bool(audit.get("idempotency_key_present")),
        "provider_status": str(audit.get("provider_status", "")),
        "lark_task_id_present": bool(audit.get("lark_task_id_present")),
        "assignee_present": bool(audit.get("assignee_present")),
    }


def _validation_node(title: str, description: str, assignee_open_id: str) -> Dict[str, object]:
    return {
        "id": "create_lark_task",
        "type": "tool_call",
        "connector": {
            "id": "lark_task",
            "kind": "lark_task",
            "operation": "create_task",
            "mode": "live",
            "request": {
                "body": {
                    "title": title,
                    "description": description,
                    "assignee_open_id": assignee_open_id,
                }
            },
            "credentials": [
                {
                    "target": "header",
                    "name": "Authorization",
                    "handle": "lark_bot_access_token",
                    "prefix": "Bearer ",
                }
            ],
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="lark_task_live_validation")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--assignee-open-id", required=True)
    parser.add_argument("--validation-run-id", required=True)
    parser.add_argument("--confirm-live-create", action="store_true")
    args = parser.parse_args(argv)
    result = run_lark_task_live_validation(
        args.repo_root,
        title=args.title,
        description=args.description,
        assignee_open_id=args.assignee_open_id,
        validation_run_id=args.validation_run_id,
        confirmed=args.confirm_live_create,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1
