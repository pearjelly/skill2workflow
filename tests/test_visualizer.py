from unittest import TestCase

from skill2workflow.visualizer import apply_litegraph_edits_to_workflow, run_overlay_for_nodes, workflow_to_litegraph


class VisualizerTests(TestCase):
    def test_workflow_to_litegraph_preserves_nodes_edges_and_properties(self):
        workflow = _approval_workflow()

        graph = workflow_to_litegraph(workflow)

        self.assertEqual(graph["version"], "skill2workflow-litegraph-0.1.0")
        self.assertEqual(graph["last_node_id"], 4)
        self.assertEqual(graph["last_link_id"], 3)
        self.assertEqual(len(graph["nodes"]), 4)
        self.assertEqual(len(graph["links"]), 3)

        start = graph["nodes"][0]
        review = graph["nodes"][1]
        self.assertEqual(start["type"], "skill2workflow/start")
        self.assertEqual(start["properties"]["workflow_node_id"], "start")
        self.assertEqual(start["properties"]["node_type"], "start")
        self.assertEqual(review["title"], "Review")
        self.assertEqual(review["type"], "skill2workflow/human_gate")
        self.assertEqual(review["properties"]["description"], "Human review gate.")
        self.assertEqual(review["properties"]["source"], {"file": "SKILL.md", "line": 12})

        start_to_review = graph["links"][0]
        self.assertEqual(start_to_review, [1, 1, 0, 2, 0, "flow"])
        self.assertEqual(start["outputs"][0]["links"], [1])
        self.assertEqual(review["inputs"][0]["link"], 1)

    def test_workflow_to_litegraph_includes_run_state_status(self):
        run_state = {
            "status": "waiting",
            "current_node": "review",
            "node_results": {
                "start": {"status": "completed"},
            },
        }

        graph = workflow_to_litegraph(_approval_workflow(), run_state=run_state)
        nodes = {node["properties"]["workflow_node_id"]: node for node in graph["nodes"]}

        self.assertEqual(nodes["start"]["properties"]["run_status"], "completed")
        self.assertEqual(nodes["review"]["properties"]["run_status"], "waiting")
        self.assertEqual(nodes["end"]["properties"]["run_status"], "not_started")

    def test_workflow_to_litegraph_attaches_read_only_run_overlay(self):
        run_state = _run_state_with_overlay_evidence()

        graph = workflow_to_litegraph(
            _authoring_workflow(),
            run_state=run_state,
            audit_events=[
                {
                    "type": "connector_completed",
                    "run_id": "run_overlay",
                    "node_id": "call_api",
                    "timestamp": "2026-07-06T00:00:03Z",
                }
            ],
        )
        nodes = {node["properties"]["workflow_node_id"]: node for node in graph["nodes"]}
        overlay = graph["extra"]["run_overlay"]

        self.assertEqual(overlay["run_id"], "run_overlay")
        self.assertEqual(overlay["status"], "completed")
        self.assertEqual(overlay["current_node"], "end")
        self.assertEqual(
            overlay["trigger"],
            {
                "trigger_id": "trigger_123",
                "source": "local-webhook",
                "idempotency_key": "event-001",
                "input_keys": ["customer_id"],
            },
        )
        self.assertNotIn("input", overlay["trigger"])
        self.assertEqual(nodes["call_api"]["properties"]["run_status"], "completed")
        self.assertEqual(
            nodes["call_api"]["properties"]["run_overlay"],
            {
                "node_id": "call_api",
                "status": "completed",
                "current": False,
                "event_count": 8,
                "latest_event_type": "node_completed",
                "result_status": "completed",
                "attempts": 2,
                "max_attempts": 1,
                "retry_count": 1,
                "recovered": True,
                "connector_id": "http",
                "connector_kind": "http",
                "connector_status": "completed",
                "error": "HTTP 503",
                "audit_event_count": 1,
            },
        )
        self.assertNotIn("output", nodes["call_api"]["properties"]["run_overlay"])
        self.assertNotIn("customer_123", str(nodes["call_api"]["properties"]["run_overlay"]))

    def test_run_overlay_for_nodes_marks_waiting_current_node(self):
        run_state = {
            "run_id": "run_waiting",
            "status": "waiting",
            "current_node": "review",
            "node_results": {"start": {"status": "completed", "timestamp": "2026-07-06T00:00:00Z"}},
            "events": [
                {"type": "node_started", "node_id": "start", "timestamp": "2026-07-06T00:00:00Z"},
                {"type": "node_completed", "node_id": "start", "timestamp": "2026-07-06T00:00:01Z"},
                {"type": "human_gate_waiting", "node_id": "review", "timestamp": "2026-07-06T00:00:02Z"},
            ],
        }

        overlay = run_overlay_for_nodes(["start", "review", "end"], run_state)

        self.assertEqual(overlay["start"]["status"], "completed")
        self.assertEqual(overlay["start"]["latest_event_type"], "node_completed")
        self.assertEqual(overlay["review"]["status"], "waiting")
        self.assertEqual(overlay["review"]["current"], True)
        self.assertEqual(overlay["review"]["latest_event_type"], "human_gate_waiting")
        self.assertEqual(overlay["end"]["status"], "not_started")

    def test_workflow_to_litegraph_derives_transition_edges_when_edges_are_absent(self):
        workflow = _approval_workflow()
        workflow["edges"] = []

        graph = workflow_to_litegraph(workflow)

        self.assertEqual(
            graph["links"],
            [
                [1, 1, 0, 2, 0, "flow"],
                [2, 2, 0, 4, 0, "flow"],
                [3, 2, 1, 3, 0, "flow"],
            ],
        )

    def test_apply_litegraph_edits_to_workflow_updates_parameters_only(self):
        workflow = _approval_workflow()
        graph = workflow_to_litegraph(workflow)
        review = next(node for node in graph["nodes"] if node["properties"]["workflow_node_id"] == "review")
        review["title"] = "Executive Review"
        review["properties"]["description"] = "Executive approval gate."

        updated = apply_litegraph_edits_to_workflow(workflow, graph)
        updated_review = next(node for node in updated["nodes"] if node["id"] == "review")
        original_review = next(node for node in workflow["nodes"] if node["id"] == "review")

        self.assertEqual(updated_review["title"], "Executive Review")
        self.assertEqual(updated_review["description"], "Executive approval gate.")
        self.assertEqual(updated_review["on_success"], "end")
        self.assertEqual(updated_review["on_failure"], "failure")
        self.assertEqual(updated_review["metadata"], {"source": {"file": "SKILL.md", "line": 12}})
        self.assertEqual(original_review["title"], "Review")

    def test_apply_litegraph_edits_to_workflow_updates_safe_authoring_fields(self):
        workflow = _authoring_workflow()
        graph = workflow_to_litegraph(workflow)
        review = next(node for node in graph["nodes"] if node["properties"]["workflow_node_id"] == "review")
        api = next(node for node in graph["nodes"] if node["properties"]["workflow_node_id"] == "call_api")

        review["properties"]["action"]["prompt"] = "Escalate to finance reviewer."
        review["properties"]["retry"]["max_attempts"] = 2
        api["properties"]["action"]["instruction"] = "Send the normalized approval payload."
        api["properties"]["connector"]["request"]["method"] = "PUT"
        api["properties"]["connector"]["request"]["url"] = "https://example.test/approval"
        api["properties"]["connector"]["request"]["headers"] = {"X-Workflow": "approval"}
        api["properties"]["connector"]["request"]["body"] = {"approved": True}
        api["properties"]["connector"]["request"]["timeout_ms"] = 1000

        updated = apply_litegraph_edits_to_workflow(workflow, graph)
        updated_review = next(node for node in updated["nodes"] if node["id"] == "review")
        updated_api = next(node for node in updated["nodes"] if node["id"] == "call_api")

        self.assertEqual(updated_review["action"]["prompt"], "Escalate to finance reviewer.")
        self.assertEqual(updated_review["retry"]["max_attempts"], 2)
        self.assertEqual(updated_api["action"]["instruction"], "Send the normalized approval payload.")
        self.assertEqual(
            updated_api["connector"],
            {
                "id": "http",
                "kind": "http",
                "request": {
                    "method": "PUT",
                    "url": "https://example.test/approval",
                    "headers": {"X-Workflow": "approval"},
                    "body": {"approved": True},
                    "timeout_ms": 1000,
                },
            },
        )
        self.assertEqual(workflow["nodes"][1]["action"]["prompt"], "Review request.")

    def test_apply_litegraph_edits_to_workflow_rejects_connector_identity_changes(self):
        workflow = _authoring_workflow()
        graph = workflow_to_litegraph(workflow)
        api = next(node for node in graph["nodes"] if node["properties"]["workflow_node_id"] == "call_api")
        api["properties"]["connector"]["id"] = "lark"

        with self.assertRaisesRegex(ValueError, "connector identity cannot be changed"):
            apply_litegraph_edits_to_workflow(workflow, graph)

    def test_apply_litegraph_edits_to_workflow_accepts_object_links(self):
        workflow = _approval_workflow()
        graph = workflow_to_litegraph(workflow)
        graph["links"] = [
            {
                "id": link[0],
                "origin_id": link[1],
                "origin_slot": link[2],
                "target_id": link[3],
                "target_slot": link[4],
                "type": link[5],
            }
            for link in graph["links"]
        ]

        updated = apply_litegraph_edits_to_workflow(workflow, graph)

        self.assertEqual(updated["nodes"], workflow["nodes"])

    def test_apply_litegraph_edits_to_workflow_rejects_topology_changes(self):
        workflow = _approval_workflow()
        graph = workflow_to_litegraph(workflow)
        graph["links"] = graph["links"][:-1]

        with self.assertRaisesRegex(ValueError, "graph topology does not match workflow DSL"):
            apply_litegraph_edits_to_workflow(workflow, graph)

    def test_apply_litegraph_edits_to_workflow_rejects_duplicate_node_mapping(self):
        workflow = _approval_workflow()
        graph = workflow_to_litegraph(workflow)
        graph["nodes"].append(dict(graph["nodes"][0]))

        with self.assertRaisesRegex(ValueError, "graph node set does not match workflow DSL"):
            apply_litegraph_edits_to_workflow(workflow, graph)


def _approval_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_approval",
            "name": "approval",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Start",
                "description": "Workflow entry point.",
                "on_success": "review",
            },
            {
                "id": "review",
                "type": "human_gate",
                "title": "Review",
                "description": "Human review gate.",
                "on_success": "end",
                "on_failure": "failure",
                "metadata": {"source": {"file": "SKILL.md", "line": 12}},
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
        ],
    }


def _authoring_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_authoring",
            "name": "authoring",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Start",
                "description": "Workflow entry point.",
                "on_success": "review",
            },
            {
                "id": "review",
                "type": "human_gate",
                "title": "Review",
                "description": "Human review gate.",
                "action": {"kind": "human_approval", "prompt": "Review request."},
                "retry": {"max_attempts": 0},
                "connector": {"id": "manual", "kind": "manual"},
                "on_success": "call_api",
                "on_failure": "failure",
                "metadata": {"source": {"file": "SKILL.md", "line": 12}},
            },
            {
                "id": "call_api",
                "type": "tool_call",
                "title": "Call API",
                "description": "Notify API.",
                "action": {"kind": "tool_call", "instruction": "Send approval payload."},
                "retry": {"max_attempts": 0},
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": "https://example.test/old",
                        "headers": {"Content-Type": "application/json"},
                        "body": {"approved": False},
                        "timeout_ms": 2000,
                    },
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_api", "from": "review", "to": "call_api", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
            {"id": "edge_api_end", "from": "call_api", "to": "end", "label": "next"},
            {"id": "edge_api_failure", "from": "call_api", "to": "failure", "label": "failure"},
        ],
    }


def _run_state_with_overlay_evidence():
    return {
        "run_id": "run_overlay",
        "status": "completed",
        "current_node": "end",
        "context": {
            "trigger": {
                "trigger_id": "trigger_123",
                "source": "local-webhook",
                "idempotency_key": "event-001",
                "input_keys": ["customer_id"],
            },
            "input": {"customer_id": "customer_123"},
        },
        "node_results": {
            "start": {"status": "completed", "title": "Start", "timestamp": "2026-07-06T00:00:00Z"},
            "review": {"status": "approved", "approved": True, "timestamp": "2026-07-06T00:00:01Z"},
            "call_api": {
                "status": "completed",
                "title": "Call API",
                "connector": {"id": "http", "kind": "http"},
                "output": {"secret_like_payload": "do-not-copy"},
                "attempts": 2,
                "max_attempts": 1,
                "last_error": "HTTP 503",
                "timestamp": "2026-07-06T00:00:03Z",
            },
            "end": {"status": "completed", "title": "End", "timestamp": "2026-07-06T00:00:04Z"},
        },
        "events": [
            {"type": "node_started", "node_id": "call_api", "timestamp": "2026-07-06T00:00:01Z"},
            {
                "type": "connector_started",
                "node_id": "call_api",
                "connector_id": "http",
                "connector_kind": "http",
                "connector_status": "running",
                "attempt": 1,
                "max_attempts": 1,
                "timestamp": "2026-07-06T00:00:01Z",
            },
            {
                "type": "connector_failed",
                "node_id": "call_api",
                "connector_id": "http",
                "connector_kind": "http",
                "connector_status": "failed",
                "attempt": 1,
                "max_attempts": 1,
                "error": "HTTP 503",
                "timestamp": "2026-07-06T00:00:02Z",
            },
            {
                "type": "node_retrying",
                "node_id": "call_api",
                "attempt": 1,
                "next_attempt": 2,
                "max_attempts": 1,
                "error": "HTTP 503",
                "timestamp": "2026-07-06T00:00:02Z",
            },
            {
                "type": "connector_started",
                "node_id": "call_api",
                "connector_id": "http",
                "connector_kind": "http",
                "connector_status": "running",
                "attempt": 2,
                "max_attempts": 1,
                "timestamp": "2026-07-06T00:00:03Z",
            },
            {
                "type": "connector_completed",
                "node_id": "call_api",
                "connector_id": "http",
                "connector_kind": "http",
                "connector_status": "completed",
                "attempt": 2,
                "max_attempts": 1,
                "timestamp": "2026-07-06T00:00:03Z",
            },
            {
                "type": "node_recovered",
                "node_id": "call_api",
                "attempt": 2,
                "max_attempts": 1,
                "error": "HTTP 503",
                "timestamp": "2026-07-06T00:00:03Z",
            },
            {"type": "node_completed", "node_id": "call_api", "timestamp": "2026-07-06T00:00:04Z"},
        ],
    }
