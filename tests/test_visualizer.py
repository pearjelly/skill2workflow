from unittest import TestCase

from skill2workflow.visualizer import workflow_to_litegraph


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
