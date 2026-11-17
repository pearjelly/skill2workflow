"""Provider-independent Agent data handoff and structured output contracts."""

import copy

from .input_schema import validate_input_schema_contract

AGENT_PROTOCOL_VERSION = "skill2workflow-agent-0.1.0"


def skill_agent_config(config):
    if (not isinstance(config, dict)
            or set(config) != {"connector", "instruction", "requires", "output_schema"}
            or not isinstance(config["connector"], str) or not config["connector"].strip()
            or config["connector"] in {"http", "http_assert", "manual"}
            or not isinstance(config["instruction"], str) or not config["instruction"].strip()
            or not isinstance(config["requires"], list)
            or any(not ((type(value) is int and value > 0) or (isinstance(value, str) and value.strip())) for value in config["requires"])
            or validate_input_schema_contract(config["output_schema"])):
        raise ValueError("Invalid Skill step annotation")
    return copy.deepcopy(config)


def agent_node_errors(node, index, schema_version):
    errors = []
    def error(code, message, field):
        errors.append({"code": code, "message": message, "path": ["nodes", index, field], "severity": "error"})
    if schema_version != "0.2.0":
        error("agent_schema_version", "agent connectors require Workflow DSL 0.2.0", "connector")
    if node.get("type") != "tool_call":
        error("agent_node_type", "agent connectors require a tool_call node", "type")
    action = node.get("action")
    if (not isinstance(action, dict) or action.get("kind") != "agent_instruction"
            or not isinstance(action.get("instruction"), str) or not action["instruction"].strip()):
        error("agent_instruction_missing", "agent requires an instruction", "action")
    requires = node.get("requires", [])
    if (not isinstance(requires, list) or any(not isinstance(value, str) or not value for value in requires)
            or (isinstance(requires, list) and all(isinstance(value, str) for value in requires) and len(set(requires)) != len(requires))):
        error("agent_requires_invalid", "agent requires must contain unique node ids", "requires")
    errors.extend(validate_input_schema_contract(node.get("output_schema"), ["nodes", index, "output_schema"]))
    return errors


def agent_request(node, context):
    """Expose only trigger input and declared successful output dependencies."""
    context = context if isinstance(context, dict) else {}
    available = context.get("nodes", {})
    selected = {}
    for dependency in node.get("requires", []):
        if dependency not in available or not isinstance(available[dependency], dict) or "output" not in available[dependency]:
            raise ValueError("agent required output is unavailable")
        selected[dependency] = {"output": copy.deepcopy(available[dependency]["output"])}
    return {"instruction": node["action"]["instruction"], "context": {
        "input": copy.deepcopy(context.get("input", {})), "nodes": selected,
    }}
