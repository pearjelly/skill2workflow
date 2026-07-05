"""Command line interface for skill2workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compiler import compile_ir_to_workflow, validate_workflow, validate_workflow_structured
from .control_plane import LocalControlPlane
from .dashboard import build_control_snapshot
from .executor import LocalExecutor
from .parser import parse_skill_file
from .visualizer import apply_litegraph_edits_to_workflow, workflow_to_litegraph


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

    resume_cmd = subparsers.add_parser("resume", help="Resume a waiting run")
    resume_cmd.add_argument("run_id")
    resume_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    resume_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
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

    trigger_cmd = subparsers.add_parser("trigger", help="Trigger a published workflow through the local API")
    trigger_cmd.add_argument("workflow_id")
    trigger_cmd.add_argument("--version", required=True)
    trigger_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    trigger_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    trigger_cmd.add_argument("--source", default="local-cli")
    trigger_cmd.add_argument("--idempotency-key", default="")
    trigger_cmd.add_argument("--input", type=Path, help="JSON object with trigger input metadata")

    resume_published_cmd = subparsers.add_parser("resume-published", help="Resume a waiting published run")
    resume_published_cmd.add_argument("run_id")
    resume_published_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    resume_published_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
    resume_published_cmd.add_argument("--reject", action="store_true")

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
    control_snapshot_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    control_snapshot_cmd.add_argument("--storage", choices=["json", "sqlite"], default="json")
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
        _print_json(LocalExecutor(args.state_dir, storage=args.storage).run(workflow))
        return 0

    if args.command == "resume":
        state = LocalExecutor(args.state_dir, storage=args.storage).resume(args.run_id, approved=not args.reject)
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
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).run_published_workflow(
                args.workflow_id, args.version
            )
        )

    if args.command == "trigger":
        return _control_action(lambda: _trigger_workflow(args))

    if args.command == "resume-published":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir, storage=args.storage).resume_published_run(
                args.run_id, approved=not args.reject
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
        snapshot = build_control_snapshot(args.state_dir, storage=args.storage)
        if args.output:
            args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            _print_json(snapshot)
        return 0

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


def _trigger_workflow(args):
    trigger_input = _load_trigger_input(args.input)
    return LocalControlPlane(args.state_dir, storage=args.storage).trigger_workflow(
        {
            "workflow_id": args.workflow_id,
            "version": args.version,
            "source": args.source,
            "idempotency_key": args.idempotency_key,
            "input": trigger_input,
        }
    )


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
