"""Prose classification must not invent executable HTTP actions."""

from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, summarize_skill_compile
from skill2workflow.connectors import default_connector_binding
from skill2workflow.parser import parse_skill_text


class InferenceTests(TestCase):
    def test_whole_words_phrases_and_chinese_terms(self):
        cases = [
            ("Generate a human-readable summary", "step", None),
            ("Fetch the latest contest results", "step", None),
            ("Send confirmation email to customer", "step", None),
            ("Rerun the pipeline", "step", None),
            ("Run the pipeline command", "step", None),
            ("Draft the report", "step", None),
            ("Ask user for approval", "human_gate", "approval"),
            ("Confirm with user before sending", "human_gate", "confirm with user"),
            ("User reviews written spec", "human_gate", "user reviews"),
            ("负责人审批", "human_gate", "审批"),
            ("提交审核材料", "human_gate", "审核"),
            ("用户确认", "human_gate", "用户确认"),
            ("校验结果", "verification", "校验"),
            ("核对订单", "verification", "核对"),
            ("Run tests", "verification", "tests"),
            ("Verification of the result", "verification", "verification"),
            ("Validate the result", "verification", "validate"),
        ]
        for title, expected, term in cases:
            with self.subTest(title=title):
                ir = parse_skill_text("## Steps\n\n1. " + title + "\n")
                workflow = compile_ir_to_workflow(ir)
                node = workflow["nodes"][1]
                self.assertEqual(node["type"], expected)
                self.assertEqual(node["metadata"]["source"]["inferred_type"], expected)
                self.assertEqual(node["metadata"]["source"]["matched_term"], term)
                self.assertEqual("connector" in node, expected == "human_gate")
                if expected == "step":
                    self.assertEqual(ir["human_gates"], [])
                    self.assertEqual(ir["verification_rules"], [])

    def test_parser_hints_use_whole_words_and_chinese_vocabulary(self):
        ir = parse_skill_text("## Steps\n1. Usefulness of reruns\n2. 最新 contest\n3. 负责人审批\n4. 验证结果\n")
        self.assertEqual(ir["tool_hints"], [])
        self.assertEqual(ir["human_gates"], ["3. 负责人审批"])
        self.assertEqual(ir["verification_rules"], ["4. 验证结果"])

    def test_only_explicit_actions_bind_http_and_review_lists_inferred_steps(self):
        ir = parse_skill_text(
            '## Steps\n1. Draft private-title-canary\n'
            '2. Call API <!-- skill2workflow: http {"request":{"url":"https://example.invalid/action"}} -->\n'
            '3. Ask user for approval\n'
        )
        workflow = compile_ir_to_workflow(ir)
        self.assertEqual(default_connector_binding("tool_call"), {})
        self.assertEqual(workflow["nodes"][2]["type"], "tool_call")
        self.assertNotIn("inferred_type", workflow["nodes"][2]["metadata"]["source"])
        notices = summarize_skill_compile(ir, workflow)["notices"]
        self.assertIn("inferred_node:1:step:", notices)
        self.assertIn("inferred_node:3:human_gate:approval", notices)
        self.assertNotIn("private-title-canary", str(notices))
