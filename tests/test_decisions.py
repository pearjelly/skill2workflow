"""DSL 0.2 decisions route durable data rather than decorative edge labels."""
import copy
import json
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow_structured
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.dashboard import build_run_detail_from_control
from skill2workflow.service_client import _validate_run_detail
from skill2workflow.decisions import condition_matches, data_context
from skill2workflow.parser import parse_skill_text
from skill2workflow.visualizer import workflow_to_litegraph, apply_litegraph_edits_to_workflow
from tests.http_fixtures import HTTPServer


SOURCE = (Path(__file__).resolve().parents[1] / "examples/skills/risk-routing/SKILL.md").read_text(encoding="utf-8")


class DecisionTests(TestCase):
    def test_conditions_are_typed_json_pointer_comparisons(self):
        context = {"input": {"amount": 12, "flag": True, "nil": None, "a/b": {"~key": ["high"]}}}
        cases = [
            ({"path": "/input/amount", "equals": 12.0}, True),
            ({"path": "/input/flag", "equals": 1}, False),
            ({"path": "/input/flag", "gt": 0}, False),
            ({"path": "/input/amount", "gt": 10}, True),
            ({"path": "/input/amount", "lt": 10}, False),
            ({"path": "/input/amount", "in": [1, 12]}, True),
            ({"path": "/input/missing", "equals": None}, False),
            ({"path": "/input/missing", "exists": False}, True),
            ({"path": "/input/nil", "exists": True}, True),
            ({"path": "/input/a~1b/~0key/0", "equals": "high"}, True),
        ]
        for condition, expected in cases:
            with self.subTest(condition=condition):
                self.assertEqual(condition_matches(condition, context), expected)

    def test_compiler_resolves_steps_and_preserves_explicit_convergence(self):
        workflow = compile_ir_to_workflow(parse_skill_text(SOURCE))
        self.assertEqual(workflow["schema_version"], "0.2.0")
        self.assertEqual(validate_workflow_structured(workflow), [])
        fetch, route, review, auto = workflow["nodes"][1:5]
        self.assertEqual(route["branches"][0]["when"]["path"], f'/nodes/{fetch["id"]}/output/body/risk')
        self.assertEqual(route["branches"][0]["to"], review["id"])
        self.assertEqual(route["default"], auto["id"])
        self.assertNotIn("on_success", route)
        self.assertEqual(review["on_success"], "end")
        for target in ("Manual approval", 3):
            changed = SOURCE.replace('"to":3', '"to":' + json.dumps(target))
            self.assertEqual(compile_ir_to_workflow(parse_skill_text(changed))["nodes"][2]["branches"][0]["to"], review["id"])

    def test_invalid_branch_contracts_targets_cycles_and_versions_are_rejected(self):
        original = compile_ir_to_workflow(parse_skill_text(SOURCE))
        modifications = [
            lambda w: w["nodes"][2].pop("default"),
            lambda w: w["nodes"][2].update(branches=[]),
            lambda w: w["nodes"][2]["branches"][0].update(to="missing"),
            lambda w: w["nodes"][2]["branches"][0].update(when={"path": "/input/x", "expr": "x > 2"}),
            lambda w: w["nodes"][2]["branches"][0].update(when={"path": "/input/x", "gt": True}),
            lambda w: w["nodes"][2]["branches"][0].update(when={"path": "/context/secret", "exists": True}),
            lambda w: w.update(schema_version="0.1.0"),
            lambda w: w["nodes"][2].update(on_success="end"),
        ]
        for mutate in modifications:
            with self.subTest(mutate=mutate):
                workflow = copy.deepcopy(original)
                mutate(workflow)
                self.assertTrue(validate_workflow_structured(workflow))
        cyclic = copy.deepcopy(original)
        cyclic["nodes"][3]["on_success"] = cyclic["nodes"][2]["id"]
        for edge in cyclic["edges"]:
            if edge["from"] == cyclic["nodes"][3]["id"] and edge["label"] == "next":
                edge["to"] = cyclic["nodes"][2]["id"]
        self.assertIn("workflow_cycle", [error["code"] for error in validate_workflow_structured(cyclic)])

    def test_graph_ports_round_trip_duplicate_destinations_and_reject_rewiring(self):
        workflow = compile_ir_to_workflow(parse_skill_text(SOURCE))
        graph = workflow_to_litegraph(workflow)
        route = next(node for node in graph["nodes"] if node["properties"]["node_type"] == "decision")
        self.assertEqual([port["name"] for port in route["outputs"]], ["branch_0", "branch_1", "default"])
        self.assertEqual(apply_litegraph_edits_to_workflow(workflow, graph), workflow)
        graph["links"][next(i for i, link in enumerate(graph["links"]) if link[1] == route["id"])][2] = 2
        with self.assertRaises(ValueError):
            apply_litegraph_edits_to_workflow(workflow, graph)

    def test_http_risk_routing_both_paths_with_restart_and_durable_evidence(self):
        class Handler(BaseHTTPRequestHandler):
            risk = "high"
            approved = 0
            def do_GET(self):
                payload = json.dumps({"risk": self.risk}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def do_POST(self):
                type(self).approved += 1
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b'{}')
            def log_message(self, *args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for storage in ("json", "sqlite"):
                for risk, amount, expected_branch in (("high", 1, 0), ("low", 20000, 1), ("low", 1, None)):
                    with self.subTest(storage=storage, risk=risk, amount=amount), TemporaryDirectory() as temporary:
                        Handler.risk, Handler.approved = risk, 0
                        workflow = compile_ir_to_workflow(parse_skill_text(SOURCE))
                        for node in workflow["nodes"]:
                            request = node.get("connector", {}).get("request")
                            if request:
                                request["url"] = request["url"].replace("https://example.invalid", f"http://127.0.0.1:{server.server_port}")
                        control = LocalControlPlane(Path(temporary), storage=storage)
                        control.publish_workflow(workflow)
                        state = control.run_published_workflow("workflow_risk_routing", "0.1.0", trigger={"input": {"amount": amount}})
                        event = next(event for event in state["events"] if event["type"] == "decision_evaluated")
                        self.assertEqual(event["branch_index"], expected_branch)
                        self.assertEqual(event["execution"], "enforced")
                        detail = build_run_detail_from_control(control, state["run_id"])
                        _validate_run_detail(detail, state["run_id"])
                        self.assertEqual(next(event for event in detail["events"] if event["type"] == "decision_evaluated")["branch_index"], expected_branch)
                        self.assertEqual(set(event), {"type", "node_id", "timestamp", "execution", "branch_index"})
                        if expected_branch is not None:
                            self.assertEqual(state["status"], "waiting")
                            self.assertEqual(Handler.approved, 0)
                            control = LocalControlPlane(Path(temporary), storage=storage)
                            state = control.resume_published_run(state["run_id"])
                        self.assertEqual(state["status"], "completed")
                        self.assertEqual(Handler.approved, 1 if expected_branch is None else 0)
                        self.assertEqual(control.inspect_run_audit(state["run_id"])["status"], "clean")
                        saved = control.get_run(state["run_id"])
                        context = data_context(saved)
                        fetch_id = workflow["nodes"][1]["id"]
                        self.assertEqual(context["nodes"][fetch_id]["output"]["body"]["risk"], risk)
                        self.assertIsInstance(saved["node_results"][fetch_id]["output"]["body"], str)
                        self.assertTrue(any(event["type"] == "decision_evaluated" for event in control.list_audit_events(run_id=state["run_id"])))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)
