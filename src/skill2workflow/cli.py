"""Command line interface for skill2workflow."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .backup import create_state_backup, restore_state_backup, verify_state_backup
from .compiler import compile_ir_to_workflow, validate_workflow, validate_workflow_structured
from .control_plane import LocalControlPlane
from .credentials import load_credential_file
from .dashboard import build_control_snapshot
from .executor import LocalExecutor
from .live_snapshot import fetch_live_control_snapshot, write_private_snapshot
from .migration import inspect_state_upgrade, upgrade_state
from .parser import parse_skill_file
from .quickstart import initialize_quickstart_workspace
from .retention import apply_state_retention, inspect_state_retention
from .schedules import LocalScheduleRunner
from .service import load_service_config, serve_runtime_service
from .service_bootstrap import initialize_service_workspace
from .service_doctor import diagnose_service
from .service_client import fetch_run_detail, post_run_cancel, post_run_resume
from .systemd_service import write_systemd_service_unit
from .telemetry import OperationalEventLogger
from .visualizer import apply_litegraph_edits_to_workflow, workflow_to_litegraph
from .webhooks import serve_webhook_requests


def main(argv=None) -> int:
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

    workflows_cmd = subparsers.add_parser("workflows", help="List published workflow versions")
    workflows_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    workflows_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

    workflow_cmd = subparsers.add_parser("workflow", help="Show a published workflow version")
    workflow_cmd.add_argument("workflow_id")
    workflow_cmd.add_argument("--version", required=True)
    workflow_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    workflow_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

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

    schedule_dispatches_cmd = subparsers.add_parser(
        "schedule-dispatches",
        help="List durable recurring-schedule dispatch records",
    )
    schedule_dispatches_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    schedule_dispatches_cmd.add_argument("--storage", choices=["json", "sqlite"], default="sqlite")
    schedule_dispatches_cmd.add_argument("--schedule-id", default="")

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

    control_runs_cmd = subparsers.add_parser("control-runs", help="List control-plane run summaries")
    control_runs_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    control_runs_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")

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
        _print_json(LocalExecutor(args.state_dir, storage=args.storage).list_runs())
        return 0

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

    if args.command == "workflows":
        _print_json(LocalControlPlane(args.state_dir, storage=args.storage).list_workflows())
        return 0

    if args.command == "workflow":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).get_workflow(
                args.workflow_id, args.version
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
        _print_json(LocalScheduleRunner(args.state_dir, storage=args.storage).list_schedules())
        return 0

    if args.command == "schedule-dispatches":
        return _control_action(
            lambda: LocalScheduleRunner(
                args.state_dir,
                storage=args.storage,
            ).list_dispatches(schedule_id=args.schedule_id)
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
            ).run_due(args.now)
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

    if args.command == "control-runs":
        _print_json(LocalControlPlane(args.state_dir, storage=args.storage).list_runs())
        return 0

    if args.command == "control-run":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).get_run(args.run_id)
        )

    if args.command == "audit":
        _print_json(
            LocalControlPlane(args.state_dir, storage=args.storage).list_audit_events(
                workflow_id=args.workflow_id,
                version=args.version,
                run_id=args.run_id,
                event_type=args.event_type,
            )
        )
        return 0

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
    return json.loads(path.read_text(encoding="utf-8"))


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
