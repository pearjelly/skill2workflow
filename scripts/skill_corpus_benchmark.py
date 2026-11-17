#!/usr/bin/env python3
"""Measure classification and executable coverage without running a workflow."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill2workflow.compiler import compile_ir_to_workflow
from skill2workflow.parser import parse_skill_file


def benchmark(corpus):
    corpus = Path(corpus)
    manifest = json.loads((corpus / "expectations.json").read_text(encoding="utf-8"))
    total = inferred = correct = false_gates = enforced = 0
    mismatches = []
    for case in manifest["cases"]:
        ir = parse_skill_file(corpus / case["path"])
        workflow = compile_ir_to_workflow(ir)
        nodes = workflow["nodes"][1:-2]
        expected = case["types"]
        if len(nodes) != len(expected):
            raise ValueError("corpus process length mismatch: " + case["path"])
        for index, (step, node, wanted) in enumerate(zip(ir["ordered_step_details"], nodes, expected), 1):
            actual = node["type"]
            total += 1
            if not step.get("node_type"):
                inferred += 1
                correct += actual == wanted
            false_gates += actual == "human_gate" and wanted != "human_gate"
            binding = node.get("connector", {})
            enforced += actual in {"human_gate", "decision"} or (
                actual == "tool_call" and isinstance(binding.get("request"), dict)
            )
            if actual != wanted:
                mismatches.append({"skill": case["path"], "step": index, "expected": wanted, "actual": actual})
    return {
        "skills": len(manifest["cases"]), "process_nodes": total,
        "inferred_nodes": inferred, "inference_accuracy": correct / inferred if inferred else 1.0,
        "false_human_gates": false_gates,
        "enforced_node_ratio": enforced / total if total else 0.0,
        "mismatches": mismatches,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "tests/fixtures/skill_corpus")
    parser.add_argument("--min-accuracy", type=float, default=1.0)
    parser.add_argument("--max-false-human-gates", type=int, default=0)
    parser.add_argument("--min-enforced-ratio", type=float, default=0.25)
    args = parser.parse_args(argv)
    result = benchmark(args.corpus)
    result["passed"] = (
        result["inference_accuracy"] >= args.min_accuracy
        and result["false_human_gates"] <= args.max_false_human_gates
        and result["enforced_node_ratio"] >= args.min_enforced_ratio
        and not result["mismatches"]
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
