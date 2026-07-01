from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow


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

