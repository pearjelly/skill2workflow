#!/usr/bin/env python3
"""Qualify explicit Agent execution through source or an installed console."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path)
    args = parser.parse_args(argv)
    program = [str(args.executable.resolve())] if args.executable else [sys.executable, "-m", "skill2workflow.cli"]
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    if args.executable is None:
        environment["PYTHONPATH"] = str(ROOT / "src")
    config = {"connector": "deterministic_agent", "instruction": "Classify request", "requires": [],
              "output_schema": {"type": "object", "properties": {
                  "risk": {"type": "string", "enum": ["high", "low"]}, "reason": {"type": "object"}},
                  "required": ["risk", "reason"], "additionalProperties": False}}
    source = ("---\nname: agent-smoke\n---\n## Steps\n"
              "1. Classify <!-- skill2workflow: agent " + json.dumps(config) + " -->\n"
              '2. Route <!-- skill2workflow: decision {"branches":[{"when":{"path":"/nodes/1/output/risk","equals":"high"},"to":3}],"default":"end"} -->\n'
              '3. Human review <!-- skill2workflow: human_gate -->\n')
    checks = {}
    with tempfile.TemporaryDirectory(prefix="skill2workflow-agent-") as temporary:
        directory = Path(temporary)
        def run(*arguments):
            result = subprocess.run(program + [str(value) for value in arguments], cwd=directory,
                                    env=environment, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeError("Agent CLI qualification failed")
            return json.loads(result.stdout)
        skill = directory / "SKILL.md"
        skill.write_text(source, encoding="utf-8")
        workflow_path = directory / "workflow.json"
        run("compile", skill.name, "-o", workflow_path, "--review")
        workflow = json.loads(workflow_path.read_text())
        checks["compiled_dsl_02"] = workflow["schema_version"] == "0.2.0"
        bundle = directory / "agent.zip"
        run("bundle-create", workflow_path, "-o", bundle)
        for storage in ("json", "sqlite"):
            for risk in ("high", "low"):
                input_path = directory / (risk + ".json")
                input_path.write_text(json.dumps({"risk": risk}))
                state_dir = directory / (storage + "-" + risk)
                state = run("bundle-run", bundle, "--input", input_path, "--state-dir", state_dir,
                            "--storage", storage, "--allow-side-effects", "--connector-fixture",
                            ROOT / "examples/connectors/deterministic_agent_connector.py")
                checks[storage + "_" + risk + "_route"] = state["status"] == ("waiting" if risk == "high" else "completed")
                agent_id = workflow["nodes"][1]["id"]
                output = state["node_results"][agent_id]["output"]
                checks[storage + "_" + risk + "_output"] = output == {"risk": risk, "reason": {"source": "deterministic"}}
                if risk == "high":
                    resumed = run("resume", state["run_id"], "--state-dir", state_dir, "--storage", storage)
                    checks[storage + "_restart"] = resumed["status"] == "completed" and resumed["node_results"][agent_id]["output"] == output
    result = {"status": "passed" if all(checks.values()) else "failed", "installed": args.executable is not None, "checks": checks}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
