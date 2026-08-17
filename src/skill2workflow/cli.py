"""Command line interface for skill2workflow."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .backup import (
    build_backup_retention_plan,
    create_state_backup,
    list_state_backups,
    restore_state_backup,
    verify_state_backup,
)
from .compiler import compile_ir_to_workflow, validate_workflow, validate_workflow_structured
from .control_plane import LocalControlPlane
from .credentials import load_credential_file
from .dashboard import build_control_snapshot, build_workflow_inventory_from_control
from .explain import build_workflow_explanation, render_workflow_explanation_text
from .preflight import build_workflow_preflight, render_workflow_preflight_text
from .executor import LocalExecutor
from .live_snapshot import fetch_live_control_snapshot, write_private_snapshot
from .migration import inspect_state_upgrade, upgrade_state
from .parser import parse_skill_file
from .quickstart import initialize_quickstart_workspace
from .retention import apply_state_retention, inspect_state_retention
from .schedules import LocalScheduleRunner
from .service import load_service_config, serve_runtime_service
from .service_bootstrap import initialize_service_workspace, rotate_service_token
from .service_doctor import diagnose_service
from .service_client import (
    fetch_audit_consistency,
    fetch_audit_events,
    fetch_recurring_schedule_list,
    fetch_recurring_schedule_dispatches,
    fetch_recurring_schedule_dispatch_page,
    fetch_workflow_artifact_report,
    fetch_workflow_inventory,
    fetch_backup_readiness,
    fetch_backup_inventory,
    fetch_backup_inventory_page,
    fetch_backup_retention_plan,
    fetch_retention_readiness,
    fetch_operational_readiness,
    fetch_service_probe,
    wait_for_service_ready,
    fetch_audit_integrity,
    fetch_runtime_info,
    fetch_workflow_diff,
    fetch_workflow_explanation,
    fetch_workflow_preflight,
    fetch_run_detail,
    fetch_run_list,
    fetch_run_page,
    fetch_support_bundle,
    post_recurring_schedule_state,
    post_recurring_schedule_create,
    put_recurring_schedule_update,
    patch_recurring_schedule,
    delete_recurring_schedule,
    post_run_cancel,
    post_run_resume,
    post_workflow_release,
    post_workflow_promotion,
    post_workflow_deprecation,
    post_workflow_trigger,
)
from .systemd_service import write_systemd_service_unit
from .telemetry import OperationalEventLogger
from .visualizer import apply_litegraph_edits_to_workflow, workflow_to_litegraph
from .webhooks import serve_webhook_requests


MAX_CLI_JSON_DOCUMENT_BYTES = 8 * 1024 * 1024


def main(argv=None) -> int:
    """Run the CLI and turn operator-input failures into stable exit codes."""

    try:
        return _main(argv)
    except (OSError, UnicodeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="skill2workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser("parse", help="Parse SKILL.md into Skill IR")
    parse_cmd.add_argument("skill", type=Path)

    compile_cmd = subparsers.add_parser("compile", help="Compile SKILL.md into Workflow DSL")
    compile_cmd.add_argument("skill", type=Path)
    compile_cmd.add_argument("-o", "--output", type=Path)

    validate_cmd = subparsers.add_parser("validate", help="Validate a Workflow DSL JSON file")
    validate_cmd.add_argument("workflow", type=Path)
    validate_cmd.add_argument("--format", choices=["text", "json"], default="text")

    explain_cmd = subparsers.add_parser(
        "explain",
        help="Show a bounded, side-effect-free execution plan for a Workflow DSL file",
    )
    explain_cmd.add_argument("workflow", type=Path)
    explain_cmd.add_argument("--format", choices=["json", "text"], default="json")

    preflight_cmd = subparsers.add_parser(
        "preflight",
        help="Check trigger input and connector mappings without executing a workflow",
    )
    preflight_cmd.add_argument("workflow", type=Path)
    preflight_cmd.add_argument("--input", type=Path)
    preflight_cmd.add_argument("--format", choices=["json", "text"], default="json")

    visualize_cmd = subparsers.add_parser("visualize", help="Convert Workflow DSL JSON into LiteGraph JSON")
    visualize_cmd.add_argument("workflow", type=Path)
    visualize_cmd.add_argument("--run-state", type=Path)
    visualize_cmd.add_argument("-o", "--output", type=Path)

    write_back_cmd = subparsers.add_parser("write-back", help="Apply safe LiteGraph edits back to Workflow DSL")
    write_back_cmd.add_argument("workflow", type=Path)
    write_back_cmd.add_argument("litegraph", type=Path)
    write_back_cmd.add_argument("-o", "--output", type=Path)

    run_cmd = subparsers.add_parser("run", help="Run a Workflow DSL JSON file")
    run_cmd.add_argument("workflow", type=Path)
    run_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    run_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    run_cmd.add_argument("--credential-file", type=Path)

    resume_cmd = subparsers.add_parser("resume", help="Resume a waiting run")
    resume_cmd.add_argument("run_id")
    resume_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    resume_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    resume_cmd.add_argument("--credential-file", type=Path)
    resume_cmd.add_argument("--reject", action="store_true")

    runs_cmd = subparsers.add_parser("runs", help="List local runs")
    runs_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    runs_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    runs_cmd.add_argument("--limit", type=int, help="Return the newest bounded run window (1-1000)")

    show_cmd = subparsers.add_parser("show", help="Show a local run detail")
    show_cmd.add_argument("run_id")
    show_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    show_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    publish_cmd = subparsers.add_parser("publish", help="Publish an immutable Workflow DSL version")
    publish_cmd.add_argument("workflow", type=Path)
    publish_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    publish_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    deprecate_cmd = subparsers.add_parser("deprecate", help="Deprecate a published workflow version")
    deprecate_cmd.add_argument("workflow_id")
    deprecate_cmd.add_argument("--version", required=True)
    deprecate_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    deprecate_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    promote_cmd = subparsers.add_parser(
        "promote", help="Point a stable alias at a published workflow version"
    )
    promote_cmd.add_argument("workflow_id")
    promote_cmd.add_argument("--version", required=True)
    promote_cmd.add_argument("--alias", default="production")
    promote_cmd.add_argument(
        "--expected-current-version",
        default="",
        help="Require the alias to still point at this version before promotion",
    )
    promote_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    promote_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    workflows_cmd = subparsers.add_parser("workflows", help="List published workflow versions")
    workflows_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    workflows_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    workflows_cmd.add_argument(
        "--limit",
        type=int,
        help="Return a compact redacted inventory window (1-100)",
    )

    workflow_artifacts_cmd = subparsers.add_parser(
        "workflow-artifacts",
        help="Inspect published workflow registry and artifact consistency",
    )
    workflow_artifacts_cmd.add_argument(
        "--state-dir", type=Path, default=Path(".skill2workflow")
    )
    workflow_artifacts_cmd.add_argument(
        "--storage", choices=["json", "sqlite"], default="json"
    )

    workflow_cmd = subparsers.add_parser("workflow", help="Show a published workflow version")
    workflow_cmd.add_argument("workflow_id")
    workflow_cmd.add_argument("--version", required=True)
    workflow_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    workflow_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    workflow_diff_cmd = subparsers.add_parser(
        "workflow-diff", help="Compare two published workflow versions without printing values"
    )
    workflow_diff_cmd.add_argument("workflow_id")
    workflow_diff_cmd.add_argument("--from-version", required=True)
    workflow_diff_cmd.add_argument("--to-version", required=True)
    workflow_diff_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    workflow_diff_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    run_published_cmd = subparsers.add_parser("run-published", help="Run a published workflow version")
    run_published_cmd.add_argument("workflow_id")
    run_published_cmd.add_argument("--version", required=True)
    run_published_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    run_published_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    run_published_cmd.add_argument("--credential-file", type=Path)

    trigger_cmd = subparsers.add_parser("trigger", help="Trigger a published workflow through the local API")
    trigger_cmd.add_argument("workflow_id")
    trigger_cmd.add_argument("--version", required=True)
    trigger_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    trigger_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    trigger_cmd.add_argument("--source", default="local-cli")
    trigger_cmd.add_argument("--idempotency-key", default="")
    trigger_cmd.add_argument("--input", type=Path, help="JSON object with trigger input metadata")
    trigger_cmd.add_argument("--credential-file", type=Path)

    schedule_add_cmd = subparsers.add_parser("schedule-add", help="Add or replace a local schedule definition")
    schedule_add_cmd.add_argument("schedule", type=Path)
    schedule_add_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    schedule_add_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    schedules_cmd = subparsers.add_parser("schedules", help="List local schedule definitions")
    schedules_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    schedules_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    schedules_cmd.add_argument("--limit", type=int, help="Return a compact newest window (1-1000)")

    schedule_dispatches_cmd = subparsers.add_parser(
        "schedule-dispatches",
        help="List durable recurring-schedule dispatch records",
    )
    schedule_dispatches_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    schedule_dispatches_cmd.add_argument("--storage", choices=["json", "sqlite"], default="sqlite")
    schedule_dispatches_cmd.add_argument("--schedule-id", default="")
    schedule_dispatches_cmd.add_argument("--limit", type=int, help="Return a compact newest window (1-1000)")

    for command, help_text in (
        ("schedule-enable", "Enable a durable recurring schedule"),
        ("schedule-disable", "Disable a durable recurring schedule"),
    ):
        schedule_state_cmd = subparsers.add_parser(command, help=help_text)
        schedule_state_cmd.add_argument("schedule_id")
        schedule_state_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
        schedule_state_cmd.add_argument("--storage", choices=["sqlite"], default="sqlite")

    schedule_run_due_cmd = subparsers.add_parser(
        "schedule-run-due",
        help="Run due local schedules through the trigger boundary",
    )
    schedule_run_due_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    schedule_run_due_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    schedule_run_due_cmd.add_argument("--now", required=True, help="ISO-8601 timestamp used for deterministic due checks")
    schedule_run_due_cmd.add_argument(
        "--max-items",
        type=int,
        help="Process at most this many due schedules (1-100)",
    )
    schedule_run_due_cmd.add_argument("--credential-file", type=Path)

    webhook_server_cmd = subparsers.add_parser(
        "webhook-server",
        help="Serve local webhook requests for published workflow triggers",
    )
    webhook_server_cmd.add_argument("--host", default="127.0.0.1")
    webhook_server_cmd.add_argument("--port", type=int, default=8080)
    webhook_server_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    webhook_server_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    webhook_server_cmd.add_argument("--credential-file", type=Path)
    webhook_server_cmd.add_argument("--once", action="store_true", help="Handle one request and then exit")

    service_cmd = subparsers.add_parser(
        "service",
        help="Run the validated self-hosted single-tenant service boundary",
    )
    service_cmd.add_argument("--config", type=Path, required=True)

    service_doctor_cmd = subparsers.add_parser(
        "service-doctor",
        help="Check self-hosted service readiness without starting it",
    )
    service_doctor_cmd.add_argument("--config", type=Path, required=True)

    service_init_cmd = subparsers.add_parser(
        "service-init",
        help="Create a secure non-overwriting self-hosted service workspace",
    )
    service_init_cmd.add_argument("--root", type=Path, required=True)
    service_init_cmd.add_argument("--host", default="127.0.0.1")
    service_init_cmd.add_argument("--port", type=int, default=8080)

    service_token_rotate_cmd = subparsers.add_parser(
        "service-token-rotate",
        help="Atomically rotate the local self-hosted service ingress token",
    )
    service_token_rotate_cmd.add_argument("--config", type=Path, required=True)

    systemd_unit_cmd = subparsers.add_parser(
        "systemd-unit",
        help="Write a hardened non-overwriting Linux systemd service unit",
    )
    systemd_unit_cmd.add_argument("--config", type=Path, required=True)
    systemd_unit_cmd.add_argument("--output", type=Path, required=True)
    systemd_unit_cmd.add_argument("--service-user", required=True)
    systemd_unit_cmd.add_argument("--service-group")
    systemd_unit_cmd.add_argument("--executable", type=Path, required=True)

    quickstart_cmd = subparsers.add_parser(
        "quickstart",
        help="Create a secure service workspace with one waiting example workflow",
    )
    quickstart_cmd.add_argument("--root", type=Path, required=True)
    quickstart_cmd.add_argument("--host", default="127.0.0.1")
    quickstart_cmd.add_argument("--port", type=int, default=8080)

    backup_cmd = subparsers.add_parser(
        "backup",
        help="Create a verified offline backup of self-hosted SQLite state",
    )
    backup_cmd.add_argument("--state-dir", type=Path, required=True)
    backup_cmd.add_argument("--output-dir", type=Path, required=True)

    backup_verify_cmd = subparsers.add_parser(
        "backup-verify",
        help="Verify a self-hosted SQLite state backup",
    )
    backup_verify_cmd.add_argument("--backup-dir", type=Path, required=True)

    backup_list_cmd = subparsers.add_parser(
        "backup-list",
        help="List bounded local SQLite backup integrity summaries",
    )
    backup_list_cmd.add_argument("--parent-dir", type=Path, required=True)
    backup_list_cmd.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Return the newest backup summaries (1-1000; default 100)",
    )

    backup_retention_plan_cmd = subparsers.add_parser(
        "backup-retention-plan",
        help="Plan bounded local backup expiration without deleting backups",
    )
    backup_retention_plan_cmd.add_argument("policy", type=Path)
    backup_retention_plan_cmd.add_argument("--parent-dir", type=Path, required=True)
    backup_retention_plan_cmd.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Inspect up to 1000 backup sets; truncation blocks the plan",
    )

    restore_cmd = subparsers.add_parser(
        "restore",
        help="Restore a verified backup into a new state directory",
    )
    restore_cmd.add_argument("--backup-dir", type=Path, required=True)
    restore_cmd.add_argument("--state-dir", type=Path, required=True)

    state_upgrade_plan_cmd = subparsers.add_parser(
        "state-upgrade-plan",
        help="Inspect whether self-hosted SQLite state requires an upgrade",
    )
    state_upgrade_plan_cmd.add_argument("--state-dir", type=Path, required=True)

    state_upgrade_cmd = subparsers.add_parser(
        "state-upgrade",
        help="Back up and copy legacy SQLite state into the current layout",
    )
    state_upgrade_cmd.add_argument("--state-dir", type=Path, required=True)
    state_upgrade_cmd.add_argument("--output-dir", type=Path, required=True)
    state_upgrade_cmd.add_argument("--backup-dir", type=Path, required=True)

    retention_plan_cmd = subparsers.add_parser(
        "state-retention-plan",
        help="Inspect aggregate data eligible for copy-on-write retention",
    )
    retention_plan_cmd.add_argument("policy", type=Path)
    retention_plan_cmd.add_argument("--state-dir", type=Path, required=True)

    retention_apply_cmd = subparsers.add_parser(
        "state-retention-apply",
        help="Publish a verified retained copy of stopped SQLite state",
    )
    retention_apply_cmd.add_argument("policy", type=Path)
    retention_apply_cmd.add_argument("--state-dir", type=Path, required=True)
    retention_apply_cmd.add_argument("--output-dir", type=Path, required=True)

    resume_published_cmd = subparsers.add_parser("resume-published", help="Resume a waiting published run")
    resume_published_cmd.add_argument("run_id")
    resume_published_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    resume_published_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    resume_published_cmd.add_argument("--credential-file", type=Path)
    resume_published_cmd.add_argument("--reject", action="store_true")

    cancel_run_cmd = subparsers.add_parser(
        "cancel-run",
        help="Request idempotent cancellation of a published run",
    )
    cancel_run_cmd.add_argument("run_id")
    cancel_run_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    cancel_run_cmd.add_argument("--storage", choices=["sqlite"], default="sqlite")

    service_resume_cmd = subparsers.add_parser(
        "service-resume",
        help="Approve or reject one waiting run through the authenticated service",
    )
    service_resume_cmd.add_argument("run_id")
    service_resume_cmd.add_argument("--service-url", required=True)
    service_resume_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_resume_cmd.add_argument("--reject", action="store_true")

    service_cancel_cmd = subparsers.add_parser(
        "service-cancel",
        help="Request cooperative cancellation through the authenticated service",
    )
    service_cancel_cmd.add_argument("run_id")
    service_cancel_cmd.add_argument("--service-url", required=True)
    service_cancel_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_show_cmd = subparsers.add_parser(
        "service-show",
        help="Show one redacted run detail through the authenticated service",
    )
    service_show_cmd.add_argument("run_id")
    service_show_cmd.add_argument("--service-url", required=True)
    service_show_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_runs_cmd = subparsers.add_parser(
        "service-runs",
        help="List bounded redacted run summaries through the authenticated service",
    )
    service_runs_cmd.add_argument("--service-url", required=True)
    service_runs_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_run_page_cmd = subparsers.add_parser(
        "service-run-page",
        help="List filtered cursor-paged redacted runs through the authenticated service",
    )
    service_run_page_cmd.add_argument("--service-url", required=True)
    service_run_page_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_run_page_cmd.add_argument("--status", default="")
    service_run_page_cmd.add_argument("--workflow-id", default="")
    service_run_page_cmd.add_argument("--cursor", default="")
    service_run_page_cmd.add_argument("--max-items", type=int, default=100)

    service_schedules_cmd = subparsers.add_parser(
        "service-recurring-schedules",
        help="List bounded recurring schedules through the authenticated service",
    )
    service_schedules_cmd.add_argument("--service-url", required=True)
    service_schedules_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_dispatches_cmd = subparsers.add_parser(
        "service-recurring-dispatches",
        help="List bounded recurring dispatch evidence through the authenticated service",
    )
    service_dispatches_cmd.add_argument("--service-url", required=True)
    service_dispatches_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_dispatches_cmd.add_argument("--schedule-id", default="")

    service_dispatch_page_cmd = subparsers.add_parser(
        "service-recurring-dispatch-page",
        help="Page recurring dispatch evidence through the authenticated service",
    )
    service_dispatch_page_cmd.add_argument("--service-url", required=True)
    service_dispatch_page_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_dispatch_page_cmd.add_argument("--schedule-id", default="")
    service_dispatch_page_cmd.add_argument("--cursor", default="")
    service_dispatch_page_cmd.add_argument("--max-items", type=int, default=100)

    service_artifacts_cmd = subparsers.add_parser(
        "service-workflow-artifacts",
        help="Inspect bounded workflow artifact consistency through the authenticated service",
    )
    service_artifacts_cmd.add_argument("--service-url", required=True)
    service_artifacts_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_backup_cmd = subparsers.add_parser(
        "service-backup-readiness",
        help="Check offline SQLite backup readiness through the authenticated service",
    )
    service_backup_cmd.add_argument("--service-url", required=True)
    service_backup_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_backup_inventory_cmd = subparsers.add_parser(
        "service-backup-inventory",
        help="List bounded redacted offline backups through the authenticated service",
    )
    service_backup_inventory_cmd.add_argument("--service-url", required=True)
    service_backup_inventory_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_backup_inventory_cmd.add_argument("--max-items", type=int, default=100)

    service_backup_inventory_page_cmd = subparsers.add_parser(
        "service-backup-inventory-page",
        help="Page redacted offline backups through the authenticated service",
    )
    service_backup_inventory_page_cmd.add_argument("--service-url", required=True)
    service_backup_inventory_page_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_backup_inventory_page_cmd.add_argument("--cursor", default="")
    service_backup_inventory_page_cmd.add_argument("--max-items", type=int, default=100)

    service_retention_cmd = subparsers.add_parser(
        "service-retention-readiness",
        help="Check retention policy readiness through the authenticated service",
    )
    service_retention_cmd.add_argument("policy", type=Path)
    service_retention_cmd.add_argument("--service-url", required=True)
    service_retention_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_backup_retention_cmd = subparsers.add_parser(
        "service-backup-retention-plan",
        help="Plan bounded remote backup expiration without deleting backups",
    )
    service_backup_retention_cmd.add_argument("policy", type=Path)
    service_backup_retention_cmd.add_argument("--service-url", required=True)
    service_backup_retention_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_operational_cmd = subparsers.add_parser(
        "service-operational-readiness",
        help="Show aggregate operational readiness through the authenticated service",
    )
    service_operational_cmd.add_argument("--service-url", required=True)
    service_operational_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_probe_cmd = subparsers.add_parser(
        "service-probe",
        help="Probe service health and readiness for deployment automation",
    )
    service_probe_cmd.add_argument("--service-url", required=True)

    service_wait_cmd = subparsers.add_parser(
        "service-wait",
        help="Wait for service readiness for deployment cutover",
    )
    service_wait_cmd.add_argument("--service-url", required=True)
    service_wait_cmd.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Maximum wait time (0 through 300 seconds; default: 60)",
    )
    service_wait_cmd.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=1.0,
        help="Delay between probes (greater than 0 through 10 seconds; default: 1)",
    )

    service_integrity_cmd = subparsers.add_parser(
        "service-audit-integrity",
        help="Verify the SQLite audit chain through the authenticated service",
    )
    service_integrity_cmd.add_argument("--service-url", required=True)
    service_integrity_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_runtime_cmd = subparsers.add_parser(
        "service-runtime-info",
        help="Show runtime version and compatibility metadata through the authenticated service",
    )
    service_runtime_cmd.add_argument("--service-url", required=True)
    service_runtime_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_workflows_cmd = subparsers.add_parser(
        "service-workflows",
        help="List bounded published Workflow DSL versions through the authenticated service",
    )
    service_workflows_cmd.add_argument("--service-url", required=True)
    service_workflows_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_diff_cmd = subparsers.add_parser(
        "service-workflow-diff",
        help="Compare two published Workflow DSL versions through the authenticated service",
    )
    service_diff_cmd.add_argument("workflow_id")
    service_diff_cmd.add_argument("--from-version", required=True)
    service_diff_cmd.add_argument("--to-version", required=True)
    service_diff_cmd.add_argument("--service-url", required=True)
    service_diff_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_explain_cmd = subparsers.add_parser(
        "service-workflow-explain",
        help="Show a bounded, value-free execution plan through the authenticated service",
    )
    service_explain_cmd.add_argument("workflow_id")
    service_explain_cmd.add_argument("--version", required=True)
    service_explain_cmd.add_argument("--service-url", required=True)
    service_explain_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_preflight_cmd = subparsers.add_parser(
        "service-workflow-preflight",
        help="Check trigger input and mappings through the authenticated service",
    )
    service_preflight_cmd.add_argument("workflow_id")
    service_preflight_cmd.add_argument("--version", required=True)
    service_preflight_cmd.add_argument("--input", type=Path)
    service_preflight_cmd.add_argument("--service-url", required=True)
    service_preflight_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_release_cmd = subparsers.add_parser(
        "service-workflow-publish",
        help="Publish one Workflow DSL document through the authenticated service",
    )
    service_release_cmd.add_argument("workflow", type=Path)
    service_release_cmd.add_argument("--service-url", required=True)
    service_release_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_promotion_cmd = subparsers.add_parser(
        "service-workflow-promote",
        help="Promote one published Workflow DSL version through the authenticated service",
    )
    service_promotion_cmd.add_argument("workflow_id")
    service_promotion_cmd.add_argument("--version", required=True)
    service_promotion_cmd.add_argument("--alias", default="production")
    service_promotion_cmd.add_argument(
        "--expected-current-version",
        default="",
        help="Require the alias to still point at this version before promotion",
    )
    service_promotion_cmd.add_argument("--service-url", required=True)
    service_promotion_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_deprecation_cmd = subparsers.add_parser(
        "service-workflow-deprecate",
        help="Deprecate one published Workflow DSL version through the authenticated service",
    )
    service_deprecation_cmd.add_argument("workflow_id")
    service_deprecation_cmd.add_argument("--version", required=True)
    service_deprecation_cmd.add_argument("--service-url", required=True)
    service_deprecation_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_trigger_cmd = subparsers.add_parser(
        "service-trigger",
        help="Trigger one published workflow through the authenticated service",
    )
    service_trigger_cmd.add_argument("workflow_id")
    service_trigger_cmd.add_argument("--version", required=True)
    service_trigger_cmd.add_argument("--service-url", required=True)
    service_trigger_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_trigger_cmd.add_argument(
        "--idempotency-key",
        required=True,
        help="Stable retry key; required to prevent duplicate remote runs",
    )
    service_trigger_cmd.add_argument("--source", default="service-cli")
    service_trigger_cmd.add_argument(
        "--input",
        type=Path,
        help="JSON object with bounded non-secret trigger input metadata",
    )

    for command, help_text in (
        ("service-schedule-enable", "Enable one recurring schedule through the authenticated service"),
        ("service-schedule-disable", "Disable one recurring schedule through the authenticated service"),
    ):
        service_schedule_state_cmd = subparsers.add_parser(command, help=help_text)
        service_schedule_state_cmd.add_argument("schedule_id")
        service_schedule_state_cmd.add_argument(
            "--expected-next-run-at",
            help="Last observed next_run_at; rejects stale enable/disable requests",
        )
        service_schedule_state_cmd.add_argument("--service-url", required=True)
        service_schedule_state_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_schedule_create_cmd = subparsers.add_parser(
        "service-recurring-schedule-add",
        help="Create or replay one recurring schedule through the authenticated service",
    )
    service_schedule_create_cmd.add_argument("schedule", type=Path)
    service_schedule_create_cmd.add_argument("--service-url", required=True)
    service_schedule_create_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_schedule_update_cmd = subparsers.add_parser(
        "service-recurring-schedule-update",
        help="Update one recurring schedule without resetting dispatch progress",
    )
    service_schedule_update_cmd.add_argument("schedule_id")
    service_schedule_update_cmd.add_argument("schedule", type=Path)
    service_schedule_update_cmd.add_argument(
        "--expected-next-run-at",
        required=True,
        help="Last observed next_run_at; prevents stale updates from overwriting progress",
    )
    service_schedule_update_cmd.add_argument("--service-url", required=True)
    service_schedule_update_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_schedule_patch_cmd = subparsers.add_parser(
        "service-recurring-schedule-patch",
        help="Patch safe recurring schedule fields without replacing trigger input",
    )
    service_schedule_patch_cmd.add_argument("schedule_id")
    service_schedule_patch_cmd.add_argument(
        "schedule",
        type=Path,
        help="JSON object containing only safe fields: workflow_id, version, starts_at, interval_seconds, missed_run_policy, enabled",
    )
    service_schedule_patch_cmd.add_argument(
        "--expected-next-run-at",
        required=True,
        help="Last observed next_run_at; prevents stale patches from overwriting progress",
    )
    service_schedule_patch_cmd.add_argument("--service-url", required=True)
    service_schedule_patch_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_schedule_delete_cmd = subparsers.add_parser(
        "service-recurring-schedule-delete",
        help="Retire one disabled recurring schedule through the authenticated service",
    )
    service_schedule_delete_cmd.add_argument("schedule_id")
    service_schedule_delete_cmd.add_argument(
        "--expected-next-run-at",
        required=True,
        help="Last observed next_run_at; prevents stale deletion from removing a changed schedule",
    )
    service_schedule_delete_cmd.add_argument("--service-url", required=True)
    service_schedule_delete_cmd.add_argument("--auth-token-file", type=Path, required=True)

    service_support_cmd = subparsers.add_parser(
        "service-support-bundle",
        help="Write a bounded redacted support bundle through the authenticated service",
    )
    service_support_cmd.add_argument("--service-url", required=True)
    service_support_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_support_cmd.add_argument("--output", type=Path, required=True)

    service_audit_cmd = subparsers.add_parser(
        "service-audit-consistency",
        help="Inspect run/audit consistency through the authenticated service",
    )
    service_audit_cmd.add_argument("--service-url", required=True)
    service_audit_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_audit_cmd.add_argument(
        "--run-id",
        default="",
        help="Inspect one run when the global bounded report is truncated",
    )

    service_audit_events_cmd = subparsers.add_parser(
        "service-audit-events",
        help="List bounded redacted audit events through the authenticated service",
    )
    service_audit_events_cmd.add_argument("--service-url", required=True)
    service_audit_events_cmd.add_argument("--auth-token-file", type=Path, required=True)
    service_audit_events_cmd.add_argument("--max-items", type=int, default=100)
    service_audit_events_cmd.add_argument("--cursor", default="")
    service_audit_events_cmd.add_argument("--workflow-id", default="")
    service_audit_events_cmd.add_argument("--workflow-version", default="")
    service_audit_events_cmd.add_argument("--run-id", default="")
    service_audit_events_cmd.add_argument("--event-type", default="")

    control_runs_cmd = subparsers.add_parser("control-runs", help="List control-plane run summaries")
    control_runs_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    control_runs_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    control_runs_cmd.add_argument("--limit", type=int, help="Return the newest bounded run window (1-1000)")

    control_run_cmd = subparsers.add_parser("control-run", help="Show a control-plane run detail")
    control_run_cmd.add_argument("run_id")
    control_run_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    control_run_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    audit_cmd = subparsers.add_parser("audit", help="List control plane audit events")
    audit_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    audit_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    audit_cmd.add_argument("--workflow-id", default="")
    audit_cmd.add_argument("--version", default="")
    audit_cmd.add_argument("--run-id", default="")
    audit_cmd.add_argument("--event-type", default="")
    audit_cmd.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Return only the newest matching events (1-1000)",
    )

    audit_consistency_cmd = subparsers.add_parser(
        "audit-consistency",
        help="Compare durable run state with control-plane audit evidence",
    )
    audit_consistency_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    audit_consistency_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    audit_consistency_cmd.add_argument("--run-id", default="")

    audit_verify_cmd = subparsers.add_parser(
        "audit-verify",
        help="Verify the SQLite audit evidence chain without printing events",
    )
    audit_verify_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    audit_verify_cmd.add_argument("--storage", choices=["json", "sqlite"], default="sqlite")

    connectors_cmd = subparsers.add_parser("connectors", help="List connector manifests")
    connectors_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    control_snapshot_cmd = subparsers.add_parser(
        "control-snapshot",
        help="Export a read-only control-plane snapshot for the local UI",
    )
    control_snapshot_cmd.add_argument("--state-dir", type=Path)
    control_snapshot_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    control_snapshot_cmd.add_argument("--service-url")
    control_snapshot_cmd.add_argument("--auth-token-file", type=Path)
    control_snapshot_cmd.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Bound an offline snapshot to the newest items (1-1000)",
    )
    control_snapshot_cmd.add_argument("-o", "--output", type=Path)

    args = parser.parse_args(argv)

    if args.command == "parse":
        _print_json(parse_skill_file(args.skill))
        return 0

    if args.command == "compile":
        workflow = compile_ir_to_workflow(parse_skill_file(args.skill))
        if args.output:
            args.output.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            _print_json(workflow)
        return 0

    if args.command == "validate":
        workflow = _load_json(args.workflow)
        structured_errors = validate_workflow_structured(workflow)
        if args.format == "json":
            _print_json(
                {
                    "valid": not structured_errors,
                    "schema_version": workflow.get("schema_version"),
                    "errors": structured_errors,
                }
            )
            return 1 if structured_errors else 0
        errors = [str(error["message"]) for error in structured_errors]
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("valid")
        return 0

    if args.command == "explain":
        workflow = _load_json(args.workflow)
        explanation = build_workflow_explanation(workflow)
        if args.format == "text":
            print(render_workflow_explanation_text(explanation), end="")
        else:
            _print_json(explanation)
        return 0

    if args.command == "preflight":
        workflow = _load_json(args.workflow)
        input_value = _load_json(args.input) if args.input else None
        report = build_workflow_preflight(
            workflow,
            input_value=input_value,
            input_present=args.input is not None,
        )
        if args.format == "text":
            print(render_workflow_preflight_text(report), end="")
        else:
            _print_json(report)
        return 0 if report["ready"] else 1

    if args.command == "visualize":
        workflow = _load_json(args.workflow)
        errors = validate_workflow(workflow)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        run_state = _load_json(args.run_state) if args.run_state else None
        graph = workflow_to_litegraph(workflow, run_state=run_state)
        if args.output:
            args.output.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            _print_json(graph)
        return 0

    if args.command == "write-back":
        try:
            updated = _write_back_workflow(_load_json(args.workflow), _load_json(args.litegraph))
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        if args.output:
            args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            _print_json(updated)
        return 0

    if args.command == "run":
        workflow = _load_json(args.workflow)
        errors = validate_workflow(workflow)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        _print_json(
            LocalExecutor(
                args.state_dir,
                storage=args.storage,
                credential_provider=_credential_provider(args),
            ).run(workflow)
        )
        return 0

    if args.command == "resume":
        state = LocalExecutor(
            args.state_dir,
            storage=args.storage,
            credential_provider=_credential_provider(args),
        ).resume(args.run_id, approved=not args.reject)
        _print_json(state)
        return 0

    if args.command == "runs":
        return _control_action(
            lambda: LocalExecutor(args.state_dir, storage=args.storage).list_runs(
                limit=args.limit
            )
        )

    if args.command == "show":
        _print_json(LocalExecutor(args.state_dir, storage=args.storage).get_run(args.run_id))
        return 0

    if args.command == "publish":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).publish_workflow(
                _load_json(args.workflow)
            )
        )

    if args.command == "deprecate":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).deprecate_workflow(
                args.workflow_id, args.version
            )
        )

    if args.command == "promote":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).promote_workflow(
                args.workflow_id,
                args.version,
                alias=args.alias,
                expected_current_version=args.expected_current_version,
            )
        )

    if args.command == "workflows":
        control = LocalControlPlane(args.state_dir, storage=args.storage)
        if args.limit is None:
            _print_json(control.list_workflows())
            return 0
        return _control_action(
            lambda: build_workflow_inventory_from_control(
                control, max_items=args.limit
            )
        )

    if args.command == "workflow-artifacts":
        return _control_action(
            lambda: LocalControlPlane(
                args.state_dir, storage=args.storage
            ).inspect_workflow_artifacts()
        )

    if args.command == "workflow":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).get_workflow(
                args.workflow_id, args.version
            )
        )

    if args.command == "workflow-diff":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).diff_workflow_versions(
                args.workflow_id, args.from_version, args.to_version
            )
        )

    if args.command == "run-published":
        return _control_action(
            lambda: LocalControlPlane(
                args.state_dir,
                storage=args.storage,
                credential_provider=_credential_provider(args),
            ).run_published_workflow(
                args.workflow_id, args.version
            )
        )

    if args.command == "trigger":
        return _control_action(lambda: _trigger_workflow(args))

    if args.command == "schedule-add":
        return _control_action(
            lambda: LocalScheduleRunner(args.state_dir, storage=args.storage).add_schedule(
                _load_json(args.schedule)
            )
        )

    if args.command == "schedules":
        runner = LocalScheduleRunner(args.state_dir, storage=args.storage)
        if args.limit is None:
            _print_json(runner.list_schedules())
            return 0
        return _control_action(lambda: runner.list_schedules_bounded(args.limit))

    if args.command == "schedule-dispatches":
        runner = LocalScheduleRunner(args.state_dir, storage=args.storage)
        if args.limit is None:
            return _control_action(
                lambda: runner.list_dispatches(schedule_id=args.schedule_id)
            )
        return _control_action(
            lambda: runner.list_dispatches_bounded(
                args.limit, schedule_id=args.schedule_id
            )
        )

    if args.command in {"schedule-enable", "schedule-disable"}:
        return _control_action(
            lambda: LocalScheduleRunner(
                args.state_dir,
                storage=args.storage,
            ).set_recurring_enabled(
                args.schedule_id,
                enabled=args.command == "schedule-enable",
            )
        )

    if args.command == "schedule-run-due":
        return _control_action(
            lambda: LocalScheduleRunner(
                args.state_dir,
                storage=args.storage,
                credential_provider=_credential_provider(args),
            ).run_due(args.now, max_items=args.max_items)
        )

    if args.command == "webhook-server":
        return _serve_webhook_server(args)

    if args.command == "service":
        return _serve_runtime_service(args)

    if args.command == "service-doctor":
        result = diagnose_service(args.config)
        _print_json(result)
        return 0 if result["status"] == "ready" else 1

    if args.command == "service-init":
        return _service_bootstrap_action(
            lambda: initialize_service_workspace(
                args.root,
                host=args.host,
                port=args.port,
            )
        )

    if args.command == "service-token-rotate":
        return _service_bootstrap_action(
            lambda: rotate_service_token(load_service_config(args.config).auth_token_file)
        )

    if args.command == "systemd-unit":
        return _systemd_unit_action(
            lambda: write_systemd_service_unit(
                args.config,
                args.output,
                service_user=args.service_user,
                service_group=args.service_group,
                executable=args.executable,
            )
        )

    if args.command == "quickstart":
        return _quickstart_action(
            lambda: initialize_quickstart_workspace(
                args.root,
                host=args.host,
                port=args.port,
            )
        )

    if args.command == "backup":
        return _backup_action(
            lambda: create_state_backup(args.state_dir, args.output_dir)
        )

    if args.command == "backup-verify":
        return _backup_action(lambda: verify_state_backup(args.backup_dir))

    if args.command == "backup-list":
        return _backup_action(
            lambda: list_state_backups(args.parent_dir, limit=args.limit)
        )

    if args.command == "backup-retention-plan":
        return _backup_action(
            lambda: build_backup_retention_plan(
                args.parent_dir,
                _load_json(args.policy),
                limit=args.limit,
            )
        )

    if args.command == "restore":
        return _backup_action(
            lambda: restore_state_backup(args.backup_dir, args.state_dir)
        )

    if args.command == "state-upgrade-plan":
        return _migration_action(lambda: inspect_state_upgrade(args.state_dir))

    if args.command == "state-upgrade":
        return _migration_action(
            lambda: upgrade_state(
                args.state_dir,
                args.output_dir,
                args.backup_dir,
            )
        )

    if args.command == "state-retention-plan":
        return _retention_action(
            lambda: inspect_state_retention(
                args.state_dir,
                _load_json(args.policy),
            )
        )

    if args.command == "state-retention-apply":
        return _retention_action(
            lambda: apply_state_retention(
                args.state_dir,
                args.output_dir,
                _load_json(args.policy),
            )
        )

    if args.command == "resume-published":
        return _control_action(
            lambda: LocalControlPlane(
                args.state_dir,
                storage=args.storage,
                credential_provider=_credential_provider(args),
            ).resume_published_run(
                args.run_id, approved=not args.reject
            )
        )

    if args.command == "cancel-run":
        return _control_action(lambda: _cancel_run(args))

    if args.command == "service-resume":
        return _service_action(
            lambda: post_run_resume(
                args.service_url,
                args.auth_token_file,
                args.run_id,
                approved=not args.reject,
            )
        )

    if args.command == "service-cancel":
        return _service_action(
            lambda: post_run_cancel(
                args.service_url,
                args.auth_token_file,
                args.run_id,
            )
        )

    if args.command == "service-show":
        return _service_action(
            lambda: fetch_run_detail(
                args.service_url,
                args.auth_token_file,
                args.run_id,
            )
        )

    if args.command == "service-runs":
        return _service_action(
            lambda: fetch_run_list(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-run-page":
        return _service_action(
            lambda: fetch_run_page(
                args.service_url,
                args.auth_token_file,
                max_items=args.max_items,
                cursor=args.cursor,
                status=args.status,
                workflow_id=args.workflow_id,
            )
        )

    if args.command == "service-recurring-schedules":
        return _service_action(
            lambda: fetch_recurring_schedule_list(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-recurring-dispatches":
        return _service_action(
            lambda: fetch_recurring_schedule_dispatches(
                args.service_url,
                args.auth_token_file,
                args.schedule_id,
            )
        )

    if args.command == "service-recurring-dispatch-page":
        return _service_action(
            lambda: fetch_recurring_schedule_dispatch_page(
                args.service_url,
                args.auth_token_file,
                schedule_id=args.schedule_id,
                max_items=args.max_items,
                cursor=args.cursor,
            )
        )

    if args.command == "service-workflow-artifacts":
        return _service_action(
            lambda: fetch_workflow_artifact_report(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-backup-readiness":
        return _service_action(
            lambda: fetch_backup_readiness(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-backup-inventory":
        return _service_action(
            lambda: fetch_backup_inventory(
                args.service_url,
                args.auth_token_file,
                max_items=args.max_items,
            )
        )

    if args.command == "service-backup-inventory-page":
        return _service_action(
            lambda: fetch_backup_inventory_page(
                args.service_url,
                args.auth_token_file,
                max_items=args.max_items,
                cursor=args.cursor,
            )
        )

    if args.command == "service-retention-readiness":
        return _service_action(
            lambda: fetch_retention_readiness(
                args.service_url,
                args.auth_token_file,
                _load_json(args.policy),
            )
        )

    if args.command == "service-backup-retention-plan":
        return _service_action(
            lambda: fetch_backup_retention_plan(
                args.service_url,
                args.auth_token_file,
                _load_json(args.policy),
            )
        )

    if args.command == "service-operational-readiness":
        return _service_action(
            lambda: fetch_operational_readiness(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-probe":
        return _service_probe_action(args.service_url)

    if args.command == "service-wait":
        return _service_wait_action(
            args.service_url,
            args.timeout_seconds,
            args.poll_interval_seconds,
        )

    if args.command == "service-audit-integrity":
        return _service_action(
            lambda: fetch_audit_integrity(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-runtime-info":
        return _service_action(
            lambda: fetch_runtime_info(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-workflows":
        return _service_action(
            lambda: fetch_workflow_inventory(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-workflow-diff":
        return _service_action(
            lambda: fetch_workflow_diff(
                args.service_url,
                args.auth_token_file,
                args.workflow_id,
                args.from_version,
                args.to_version,
            )
        )

    if args.command == "service-workflow-explain":
        return _service_action(
            lambda: fetch_workflow_explanation(
                args.service_url,
                args.auth_token_file,
                args.workflow_id,
                args.version,
            )
        )

    if args.command == "service-workflow-preflight":
        return _service_preflight_action(
            lambda: fetch_workflow_preflight(
                args.service_url,
                args.auth_token_file,
                args.workflow_id,
                args.version,
                input_value=_load_json(args.input) if args.input else None,
                input_present=args.input is not None,
            )
        )

    if args.command == "service-workflow-publish":
        return _service_action(
            lambda: post_workflow_release(
                args.service_url,
                args.auth_token_file,
                _load_json(args.workflow),
            )
        )

    if args.command == "service-workflow-promote":
        return _service_action(
            lambda: post_workflow_promotion(
                args.service_url,
                args.auth_token_file,
                args.workflow_id,
                args.version,
                alias=args.alias,
                expected_current_version=args.expected_current_version,
            )
        )

    if args.command == "service-workflow-deprecate":
        return _service_action(
            lambda: post_workflow_deprecation(
                args.service_url,
                args.auth_token_file,
                args.workflow_id,
                args.version,
            )
        )

    if args.command == "service-trigger":
        return _service_action(
            lambda: post_workflow_trigger(
                args.service_url,
                args.auth_token_file,
                args.workflow_id,
                args.version,
                idempotency_key=args.idempotency_key,
                source=args.source,
                trigger_input=_load_trigger_input(args.input),
            )
        )

    if args.command in {"service-schedule-enable", "service-schedule-disable"}:
        state_kwargs = {}
        if args.expected_next_run_at is not None:
            state_kwargs["expected_next_run_at"] = args.expected_next_run_at
        return _service_action(
            lambda: post_recurring_schedule_state(
                args.service_url,
                args.auth_token_file,
                args.schedule_id,
                enabled=args.command == "service-schedule-enable",
                **state_kwargs,
            )
        )

    if args.command == "service-recurring-schedule-add":
        return _service_action(
            lambda: post_recurring_schedule_create(
                args.service_url,
                args.auth_token_file,
                _load_json(args.schedule),
            )
        )

    if args.command == "service-recurring-schedule-update":
        return _service_action(
            lambda: put_recurring_schedule_update(
                args.service_url,
                args.auth_token_file,
                args.schedule_id,
                _load_json(args.schedule),
                expected_next_run_at=args.expected_next_run_at,
            )
        )

    if args.command == "service-recurring-schedule-patch":
        return _service_action(
            lambda: patch_recurring_schedule(
                args.service_url,
                args.auth_token_file,
                args.schedule_id,
                _load_json(args.schedule),
                expected_next_run_at=args.expected_next_run_at,
            )
        )

    if args.command == "service-recurring-schedule-delete":
        return _service_action(
            lambda: delete_recurring_schedule(
                args.service_url,
                args.auth_token_file,
                args.schedule_id,
                expected_next_run_at=args.expected_next_run_at,
            )
        )

    if args.command == "service-support-bundle":
        try:
            bundle = fetch_support_bundle(args.service_url, args.auth_token_file)
            write_private_snapshot(args.output, bundle)
            _print_json(
                {
                    "schema_version": bundle["schema_version"],
                    "output": str(args.output),
                }
            )
            return 0
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        except OSError:
            print("support bundle operation failed", file=sys.stderr)
            return 1

    if args.command == "service-audit-consistency":
        if args.run_id:
            return _service_action(
                lambda: fetch_audit_consistency(
                    args.service_url,
                    args.auth_token_file,
                    args.run_id,
                )
            )
        return _service_action(
            lambda: fetch_audit_consistency(
                args.service_url,
                args.auth_token_file,
            )
        )

    if args.command == "service-audit-events":
        return _service_action(
            lambda: fetch_audit_events(
                args.service_url,
                args.auth_token_file,
                max_items=args.max_items,
                cursor=args.cursor,
                workflow_id=args.workflow_id,
                workflow_version=args.workflow_version,
                run_id=args.run_id,
                event_type=args.event_type,
            )
        )

    if args.command == "control-runs":
        return _control_action(
            lambda: LocalControlPlane(
                args.state_dir, storage=args.storage
            ).list_runs(limit=args.limit)
        )

    if args.command == "control-run":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).get_run(args.run_id)
        )

    if args.command == "audit":
        return _control_action(
            lambda: LocalControlPlane(
                args.state_dir, storage=args.storage
            ).list_audit_events(
                workflow_id=args.workflow_id,
                version=args.version,
                run_id=args.run_id,
                event_type=args.event_type,
                limit=args.limit,
            )
        )

    if args.command == "audit-consistency":
        return _control_action(
            lambda: LocalControlPlane(
                args.state_dir, storage=args.storage
            ).inspect_run_audit(run_id=args.run_id)
        )

    if args.command == "audit-verify":
        result = LocalControlPlane(args.state_dir, storage=args.storage).verify_audit_integrity()
        _print_json(result)
        return 0 if result.get("status") == "valid" else 1

    if args.command == "connectors":
        _print_json(LocalControlPlane(args.state_dir).list_connectors())
        return 0

    if args.command == "control-snapshot":
        try:
            if args.service_url:
                if args.auth_token_file is None or args.state_dir is not None:
                    raise ValueError(
                        "live control snapshot requires --auth-token-file and excludes --state-dir"
                    )
                if args.max_items is not None:
                    raise ValueError("--max-items is only valid for offline snapshots")
                snapshot = fetch_live_control_snapshot(
                    args.service_url,
                    args.auth_token_file,
                )
            else:
                if args.auth_token_file is not None:
                    raise ValueError("--auth-token-file requires --service-url")
                snapshot = build_control_snapshot(
                    args.state_dir or Path(".skill2workflow"),
                    storage=args.storage,
                    max_items=args.max_items,
                )
            if args.output:
                write_private_snapshot(args.output, snapshot)
            else:
                _print_json(snapshot)
            return 0
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        except OSError:
            print("control snapshot operation failed", file=sys.stderr)
            return 1

    return 1


def _load_json(path: Path):
    try:
        if path.stat().st_size > MAX_CLI_JSON_DOCUMENT_BYTES:
            raise ValueError(
                f"JSON document exceeds {MAX_CLI_JSON_DOCUMENT_BYTES} bytes"
            )
        with path.open("rb") as handle:
            raw = handle.read(MAX_CLI_JSON_DOCUMENT_BYTES + 1)
    except OSError:
        raise
    if len(raw) > MAX_CLI_JSON_DOCUMENT_BYTES:
        raise ValueError(
            f"JSON document exceeds {MAX_CLI_JSON_DOCUMENT_BYTES} bytes"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("JSON document must be UTF-8") from error
    try:
        return json.loads(text)
    except RecursionError as error:
        raise ValueError("JSON document nesting is too deep") from error


def _print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _control_action(callback) -> int:
    try:
        _print_json(callback())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("run not found", file=sys.stderr)
        return 1


def _service_action(callback) -> int:
    try:
        _print_json(callback())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except OSError:
        print("service action failed", file=sys.stderr)
        return 1


def _service_preflight_action(callback) -> int:
    try:
        result = callback()
        _print_json(result)
        return 0 if result.get("ready") is True else 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except OSError:
        print("service action failed", file=sys.stderr)
        return 1


def _service_probe_action(service_url: str) -> int:
    try:
        result = fetch_service_probe(service_url)
        _print_json(result)
        return {"ready": 0, "not_ready": 1, "unavailable": 2}[result["status"]]
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


def _service_wait_action(
    service_url: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> int:
    try:
        result = wait_for_service_ready(
            service_url,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        _print_json(result)
        return {"ready": 0, "not_ready": 1, "unavailable": 2}[result["status"]]
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


def _backup_action(callback) -> int:
    try:
        _print_json(callback())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error):
        print("state backup operation failed", file=sys.stderr)
        return 1


def _migration_action(callback) -> int:
    try:
        _print_json(callback())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error):
        print("state upgrade operation failed", file=sys.stderr)
        return 1


def _retention_action(callback) -> int:
    try:
        _print_json(callback())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error):
        print("state retention operation failed", file=sys.stderr)
        return 1


def _service_bootstrap_action(callback) -> int:
    try:
        _print_json(callback())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except OSError:
        print("service bootstrap operation failed", file=sys.stderr)
        return 1


def _quickstart_action(callback) -> int:
    try:
        _print_json(callback())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except OSError:
        print("quickstart operation failed", file=sys.stderr)
        return 1


def _trigger_workflow(args):
    trigger_input = _load_trigger_input(args.input)
    return LocalControlPlane(
        args.state_dir,
        storage=args.storage,
        credential_provider=_credential_provider(args),
    ).trigger_workflow(
        {
            "workflow_id": args.workflow_id,
            "version": args.version,
            "source": args.source,
            "idempotency_key": args.idempotency_key,
            "input": trigger_input,
        }
    )


def _cancel_run(args):
    state = LocalControlPlane(
        args.state_dir,
        storage=args.storage,
    ).cancel_published_run(args.run_id)
    return {
        "run_id": str(state["run_id"]),
        "status": str(state["status"]),
    }


def _serve_webhook_server(args) -> int:
    try:
        serve_webhook_requests(
            host=args.host,
            port=args.port,
            control_plane=LocalControlPlane(
                args.state_dir,
                storage=args.storage,
                credential_provider=_credential_provider(args),
            ),
            once=args.once,
        )
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


def _serve_runtime_service(args) -> int:
    try:
        serve_runtime_service(
            load_service_config(args.config),
            event_logger=OperationalEventLogger(),
        )
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


def _systemd_unit_action(action) -> int:
    try:
        _print_json(action())
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


def _credential_provider(args):
    path = getattr(args, "credential_file", None)
    if path is None:
        return None
    return load_credential_file(path)


def _load_trigger_input(path: Path):
    if path is None:
        return {}
    value = _load_json(path)
    if not isinstance(value, dict):
        raise ValueError("trigger input must be a JSON object")
    return value


def _write_back_workflow(workflow, graph):
    updated = apply_litegraph_edits_to_workflow(workflow, graph)
    errors = validate_workflow(updated)
    if errors:
        raise ValueError("; ".join(errors))
    return updated


if __name__ == "__main__":
    raise SystemExit(main())
