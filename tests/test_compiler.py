from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow, validate_workflow_structured


class CompilerTests(TestCase):
    def test_compile_ordered_steps_to_valid_workflow(self):
        ir = {
            "metadata": {"name": "approval-flow", "description": "Approval workflow"},
            "hard_gates": ["Do NOT publish until the user approves the draft."],
            "ordered_steps": ["Explore", "Ask user for approval", "Publish"],
            "tool_hints": [],
            "human_gates": [],
            "verification_rules": [],
            "source_path": "SKILL.md",
        }

        workflow = compile_ir_to_workflow(ir)
        errors = validate_workflow(workflow)

        self.assertEqual(errors, [])
        self.assertEqual(workflow["entry"], "start")
        self.assertIn(
            "node_002_ask_user_for_approval",
            {node["id"] for node in workflow["nodes"]},
        )
        human_node = next(
            node
            for node in workflow["nodes"]
            if node["id"] == "node_002_ask_user_for_approval"
        )
        self.assertEqual(human_node["type"], "human_gate")

    def test_compile_uses_ordered_step_details_for_node_metadata(self):
        ir = {
            "metadata": {"name": "brainstorming", "description": "Design workflow"},
            "hard_gates": [],
            "ordered_steps": [
                "Explore project context — check files, docs, recent commits",
                "User reviews written spec — ask user to review the spec file before proceeding",
            ],
            "ordered_step_details": [
                {
                    "title": "Explore project context",
                    "detail": "check files, docs, recent commits",
                    "line": 24,
                    "section": "Checklist",
                },
                {
                    "title": "User reviews written spec",
                    "detail": "ask user to review the spec file before proceeding",
                    "line": 31,
                    "section": "Checklist",
                },
            ],
            "tool_hints": [],
            "human_gates": [],
            "verification_rules": [],
            "source_path": "skills/brainstorming/SKILL.md",
        }

        workflow = compile_ir_to_workflow(ir)

        explore = next(node for node in workflow["nodes"] if node["id"] == "node_001_explore_project_context")
        review = next(node for node in workflow["nodes"] if node["id"] == "node_002_user_reviews_written_spec")

        self.assertEqual(explore["title"], "Explore project context")
        self.assertEqual(explore["description"], "check files, docs, recent commits")
        self.assertEqual(
            explore["metadata"]["source"],
            {
                "file": "skills/brainstorming/SKILL.md",
                "kind": "ordered_step",
                "index": 1,
                "line": 24,
                "section": "Checklist",
            },
        )
        self.assertEqual(review["type"], "human_gate")

    def test_compile_binds_default_connectors_for_connector_nodes(self):
        ir = {
            "metadata": {"name": "tool-flow", "description": "Tool workflow"},
            "hard_gates": [],
            "ordered_steps": [
                "Run tool to fetch account data",
                "Ask user for approval",
            ],
            "tool_hints": [],
            "human_gates": [],
            "verification_rules": [],
            "source_path": "SKILL.md",
        }

        workflow = compile_ir_to_workflow(ir)
        errors = validate_workflow(workflow)

        tool_node = next(node for node in workflow["nodes"] if node["type"] == "tool_call")
        human_node = next(node for node in workflow["nodes"] if node["type"] == "human_gate")
        self.assertEqual(errors, [])
        self.assertEqual(tool_node["connector"]["id"], "http")
        self.assertEqual(tool_node["connector"]["kind"], "http")
        self.assertEqual(human_node["connector"]["id"], "manual")
        self.assertEqual(human_node["connector"]["kind"], "manual")

    def test_validate_rejects_invalid_edges(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {
                "id": "workflow_invalid",
                "name": "invalid",
                "version": "0.1.0",
                "status": "draft",
            },
            "entry": "start",
            "nodes": [
                {"id": "start", "type": "start", "title": "Start", "on_success": "step"},
                {"id": "step", "type": "step", "title": "Step", "on_success": "end", "on_failure": "failure"},
                {"id": "failure", "type": "failure", "title": "Failure"},
                {"id": "end", "type": "end", "title": "End"},
            ],
            "edges": [
                {"id": "edge_1", "from": "start", "to": "missing", "condition": None, "label": "next"},
                {"id": "edge_1", "from": "step", "to": "end", "condition": None, "label": "next"},
                {"id": "edge_extra", "from": "start", "to": "end", "condition": None, "label": "next"},
            ],
        }

        errors = validate_workflow(workflow)

        self.assertIn("edge ids must be unique", errors)
        self.assertIn("edge_1.to references missing node missing", errors)
        self.assertIn("start.on_success must have matching edge to step", errors)
        self.assertIn("edge_extra from start to end is not declared by node transitions", errors)

    def test_validate_rejects_end_nodes_with_outgoing_edges(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {
                "id": "workflow_bad_end",
                "name": "bad-end",
                "version": "0.1.0",
                "status": "draft",
            },
            "entry": "start",
            "nodes": [
                {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
                {"id": "end", "type": "end", "title": "End", "on_success": "start"},
            ],
            "edges": [
                {"id": "edge_1", "from": "start", "to": "end", "condition": None, "label": "next"},
                {"id": "edge_2", "from": "end", "to": "start", "condition": None, "label": "next"},
            ],
        }

        errors = validate_workflow(workflow)

        self.assertIn("end end must not define on_success", errors)
        self.assertIn("edge_2 must not originate from terminal node end", errors)

    def test_validate_rejects_tool_call_without_connector_binding(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {
                "id": "workflow_missing_connector",
                "name": "missing-connector",
                "version": "0.1.0",
                "status": "draft",
            },
            "entry": "start",
            "nodes": [
                {"id": "start", "type": "start", "title": "Start", "on_success": "tool"},
                {"id": "tool", "type": "tool_call", "title": "Call tool", "on_success": "end"},
                {"id": "end", "type": "end", "title": "End"},
            ],
            "edges": [
                {"id": "edge_start_tool", "from": "start", "to": "tool", "label": "next"},
                {"id": "edge_tool_end", "from": "tool", "to": "end", "label": "next"},
            ],
        }

        errors = validate_workflow_structured(workflow)

        self.assertTrue(any(error["code"] == "connector_binding_missing" for error in errors))
