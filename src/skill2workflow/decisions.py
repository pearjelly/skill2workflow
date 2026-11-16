"""Deterministic decisions over persisted JSON data; never evaluate source."""

import copy
import math
import re

from .http_assertions import MISSING, json_pointer_value, json_scalar_equal, load_assertion_json

OPERATORS = {"equals", "in", "exists", "gt", "lt"}


def valid_data_pointer(path):
    if not isinstance(path, str):
        return False
    if len(path.encode("utf-8")) > 1024 or path.count("/") > 32 or re.search(r"~(?![01])", path):
        return False
    return bool(path == "/input" or path.startswith("/input/")
                or re.fullmatch(r"/nodes/[^/]+/output(?:/.*)?", path))


def valid_condition(condition):
    if not isinstance(condition, dict) or not valid_data_pointer(condition.get("path")):
        return False
    operators = set(condition) - {"path"}
    if len(operators) != 1 or not operators <= OPERATORS:
        return False
    operator = next(iter(operators))
    value = condition[operator]
    if operator == "exists":
        return type(value) is bool
    if operator in {"gt", "lt"}:
        return type(value) in (int, float) and (not isinstance(value, float) or math.isfinite(value))
    values = value if operator == "in" else [value]
    return (isinstance(values, list) and bool(values)
            and all(type(item) in (str, int, float, bool, type(None))
                    and (not isinstance(item, float) or math.isfinite(item)) for item in values))


def condition_matches(condition, context):
    actual = json_pointer_value(context, condition["path"])
    if "exists" in condition:
        return (actual is not MISSING) == condition["exists"]
    if actual is MISSING:
        return False
    if "equals" in condition:
        return json_scalar_equal(actual, condition["equals"])
    if "in" in condition:
        return any(json_scalar_equal(actual, value) for value in condition["in"])
    if type(actual) not in (int, float):
        return False
    if "gt" in condition:
        return actual > condition["gt"]
    return actual < condition["lt"]


def data_context(state):
    """Build a detached evaluation view from successful durable outputs."""
    context = {"input": copy.deepcopy(state.get("context", {}).get("input", {})), "nodes": {}}
    for node_id, result in state.get("node_results", {}).items():
        if result.get("status") != "completed" or "output" not in result:
            continue
        output = copy.deepcopy(result["output"])
        if (isinstance(output, dict) and result.get("connector", {}).get("id") == "http"
                and isinstance(output.get("body"), str)):
            try:
                output["body"] = load_assertion_json(output["body"])
            except (ValueError, TypeError, RecursionError, OverflowError):
                pass
        context["nodes"][node_id] = {"output": output}
    return context


def evaluate_decision(node, context):
    for index, branch in enumerate(node["branches"]):
        if condition_matches(branch["when"], context):
            return branch["to"], index
    return node["default"], None


def decision_errors(node, index, node_ids, schema_version):
    errors = []
    def error(code, message, path):
        errors.append({"code": code, "message": message, "path": ["nodes", index] + path, "severity": "error"})
    if schema_version != "0.2.0":
        error("decision_schema_version", "decision requires Workflow DSL 0.2.0", ["type"])
    if any(key in node for key in ("on_success", "on_failure", "on_fallback", "connector")):
        error("decision_transition_invalid", "decision uses branches/default only", [])
    branches = node.get("branches")
    if not isinstance(branches, list) or not branches:
        error("decision_branches_invalid", "decision requires nonempty ordered branches", ["branches"])
        branches = []
    for branch_index, branch in enumerate(branches):
        path = ["branches", branch_index]
        if not isinstance(branch, dict) or set(branch) != {"when", "to"}:
            error("decision_branch_invalid", "decision branch requires when and to", path)
            continue
        if not valid_condition(branch["when"]):
            error("decision_condition_invalid", "decision condition is invalid", path + ["when"])
        elif branch["when"]["path"].startswith("/nodes/"):
            dependency = branch["when"]["path"].split("/")[2].replace("~1", "/").replace("~0", "~")
            if dependency not in node_ids:
                error("decision_source_missing", "decision source node does not exist", path + ["when", "path"])
        if not isinstance(branch.get("to"), str) or branch["to"] not in node_ids:
            error("decision_target_missing", "decision branch target does not exist", path + ["to"])
    if not isinstance(node.get("default"), str) or node["default"] not in node_ids:
        error("decision_default_missing", "decision requires an existing default target", ["default"])
    return errors
