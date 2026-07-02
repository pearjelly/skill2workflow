"""Command line interface for skill2workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compiler import compile_ir_to_workflow, validate_workflow, validate_workflow_structured
from .control_plane import LocalControlPlane
from .executor import LocalExecutor
from .parser import parse_skill_file
from .visualizer import workflow_to_litegraph


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

    run_cmd = subparsers.add_parser("run", help="Run a Workflow DSL JSON file")
    run_cmd.add_argument("workflow", type=Path)
    run_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    resume_cmd = subparsers.add_parser("resume", help="Resume a waiting run")
    resume_cmd.add_argument("run_id")
    resume_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))
    resume_cmd.add_argument("--reject", action="store_true")

    runs_cmd = subparsers.add_parser("runs", help="List local runs")
    runs_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    show_cmd = subparsers.add_parser("show", help="Show a local run detail")
    show_cmd.add_argument("run_id")
    show_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    publish_cmd = subparsers.add_parser("publish", help="Publish an immutable Workflow DSL version")
    publish_cmd.add_argument("workflow", type=Path)
    publish_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    deprecate_cmd = subparsers.add_parser("deprecate", help="Deprecate a published workflow version")
    deprecate_cmd.add_argument("workflow_id")
    deprecate_cmd.add_argument("--version", required=True)
    deprecate_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    workflows_cmd = subparsers.add_parser("workflows", help="List published workflow versions")
    workflows_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    workflow_cmd = subparsers.add_parser("workflow", help="Show a published workflow version")
    workflow_cmd.add_argument("workflow_id")
    workflow_cmd.add_argument("--version", required=True)
    workflow_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    run_published_cmd = subparsers.add_parser("run-published", help="Run a published workflow version")
    run_published_cmd.add_argument("workflow_id")
    run_published_cmd.add_argument("--version", required=True)
    run_published_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    audit_cmd = subparsers.add_parser("audit", help="List control plane audit events")
    audit_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

    connectors_cmd = subparsers.add_parser("connectors", help="List connector registry placeholders")
    connectors_cmd.add_argument("--state-dir", type=Path, default=Path(".skill2workflow"))

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

    if args.command == "run":
        workflow = _load_json(args.workflow)
        errors = validate_workflow(workflow)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        _print_json(LocalExecutor(args.state_dir).run(workflow))
        return 0

    if args.command == "resume":
        state = LocalExecutor(args.state_dir).resume(args.run_id, approved=not args.reject)
        _print_json(state)
        return 0

    if args.command == "runs":
        _print_json(LocalExecutor(args.state_dir).list_runs())
        return 0

    if args.command == "show":
        _print_json(LocalExecutor(args.state_dir).get_run(args.run_id))
        return 0

    if args.command == "publish":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir).publish_workflow(_load_json(args.workflow))
        )

    if args.command == "deprecate":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir).deprecate_workflow(args.workflow_id, args.version)
        )

    if args.command == "workflows":
        _print_json(LocalControlPlane(args.state_dir).list_workflows())
        return 0

    if args.command == "workflow":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir).get_workflow(args.workflow_id, args.version)
        )

    if args.command == "run-published":
        return _control_action(
            lambda: LocalControlPlane(args.state_dir).run_published_workflow(args.workflow_id, args.version)
        )

    if args.command == "audit":
        _print_json(LocalControlPlane(args.state_dir).list_audit_events())
        return 0

    if args.command == "connectors":
        _print_json(LocalControlPlane(args.state_dir).list_connectors())
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


if __name__ == "__main__":
    raise SystemExit(main())
