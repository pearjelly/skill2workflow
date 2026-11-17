"""Known-field JSON shapes shared by the hand-written DSL validation path.

This is a workflow shape check, not a JSON Schema engine. Graph, pointer,
input-contract and connector semantics remain in their domain validators.
Unknown extension properties retain the schemas' additionalProperties policy.
"""

from typing import Any, Dict, List, Tuple

NODE_TYPES = {"start", "step", "human_gate", "tool_call", "verification", "instruction", "decision", "failure", "end"}


def validate_workflow_shapes(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []

    def issue(path, code="workflow_field_invalid"):
        label = ".".join(str(value) for value in path)
        errors.append({"code": code, "message": f"workflow.{label} does not match the documented JSON shape", "path": path, "severity": "error"})

    def field(obj, key, kinds: Tuple[type, ...], path, required=False, nonempty=False, code="workflow_field_invalid"):
        if key not in obj:
            if required:
                issue(path + [key], code)
            return
        value = obj[key]
        if not isinstance(value, kinds) or (kinds == (int,) and type(value) is bool) or (nonempty and not value):
            issue(path + [key], code)

    if "entry" in workflow:
        field(workflow, "entry", (str,), [], nonempty=True, code="entry_missing")
    if "edges" not in workflow:
        issue(["edges"], "edges_not_list")
    meta = workflow.get("workflow")
    if isinstance(meta, dict):
        for key in ("id", "name", "version", "status"):
            field(meta, key, (str,), ["workflow"], required=True, nonempty=True)
        field(meta, "description", (str,), ["workflow"])
        if isinstance(meta.get("status"), str) and meta["status"] not in {"draft", "published", "deprecated"}:
            issue(["workflow", "status"])
    field(workflow, "state_schema", (dict,), [])
    field(workflow, "policies", (dict,), [])
    if isinstance(workflow.get("policies"), dict):
        field(workflow["policies"], "default_retry", (dict,), ["policies"])
    for key in ("guards", "checkpoints"):
        field(workflow, key, (list,), [])
        if isinstance(workflow.get(key), list):
            for index, item in enumerate(workflow[key]):
                if not isinstance(item, dict):
                    issue([key, index])
                elif key == "guards":
                    field(item, "id", (str,), [key, index], required=True, nonempty=True)
                    field(item, "description", (str,), [key, index], required=True)
    nodes = workflow.get("nodes")
    for index, node in enumerate(nodes if isinstance(nodes, list) else []):
        if not isinstance(node, dict):
            continue
        path = ["nodes", index]
        for key in ("id", "type", "title"):
            field(node, key, (str,), path, required=True, nonempty=True, code=f"node_{key}_invalid")
        if isinstance(node.get("type"), str) and node["type"] not in NODE_TYPES:
            issue(path + ["type"], "node_type_invalid")
        for key, kinds in (("description", (str,)), ("metadata", (dict,)), ("action", (dict, type(None))),
                           ("guard", (dict, str, type(None))), ("on_success", (str,)),
                           ("on_failure", (str,)), ("on_fallback", (str,))):
            field(node, key, kinds, path, nonempty=key in {"on_success", "on_failure", "on_fallback"})
        for key in ("requires", "produces"):
            field(node, key, (list,), path)
            if isinstance(node.get(key), list) and any(not isinstance(item, str) for item in node[key]):
                issue(path + [key])
        binding = node.get("connector")
        if not isinstance(binding, dict):
            continue
        binding_id = binding.get("id")
        http_binding = isinstance(binding_id, str) and binding_id in {"http", "http_assert"}
        if "id" in binding and binding["id"] and not isinstance(binding["id"], str):
            issue(path + ["connector", "id"], "connector_binding_invalid")
        field(binding, "kind", (str,), path + ["connector"], code="connector_binding_invalid")
        field(binding, "credentials", (list,), path + ["connector"])
        request = binding.get("request")
        if "request" in binding and not isinstance(request, dict) and not http_binding:
            issue(path + ["connector", "request"])
        if isinstance(request, dict):
            for key, kinds in (("url", (str,)), ("method", (str,)), ("headers", (dict,)), ("timeout_ms", (int,))):
                field(request, key, kinds, path + ["connector", "request"])
        if "assertions" in binding and binding_id != "http_assert":
            checks = binding["assertions"]
            checks_path = path + ["connector", "assertions"]
            if not isinstance(checks, list) or not 1 <= len(checks) <= 16:
                issue(checks_path)
            else:
                for check_index, check in enumerate(checks):
                    if (not isinstance(check, dict) or set(check) != {"path", "equals"}
                            or not isinstance(check["path"], str) or len(check["path"]) > 1024
                            or (check["path"] and not check["path"].startswith("/"))
                            or type(check["equals"]) not in (str, int, float, bool, type(None))):
                        issue(checks_path + [check_index])
    edges = workflow.get("edges")
    for index, edge in enumerate(edges if isinstance(edges, list) else []):
        if not isinstance(edge, dict):
            continue
        path = ["edges", index]
        for key in ("id", "from", "to"):
            field(edge, key, (str,), path, required=True, nonempty=True)
        field(edge, "label", (str, type(None)), path)
        field(edge, "condition", (dict, str, type(None)), path)
    return errors
