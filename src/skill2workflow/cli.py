"""Command line interface for skill2workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compiler import compile_ir_to_workflow, validate_workflow
from .executor import LocalExecutor
from .parser import parse_skill_file


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
        errors = validate_workflow(workflow)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("valid")
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

    return 1


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
