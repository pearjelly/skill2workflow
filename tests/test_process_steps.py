from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, summarize_skill_compile, validate_workflow
from skill2workflow.executor import LocalExecutor
from skill2workflow.parser import parse_skill_text


AMBIGUOUS_PROCESS = (
    "SKILL.md has multiple Workflow or Steps sections; "
    "use one process section or an explicit Checklist"
)


class ProcessStepTests(TestCase):
    def test_exact_process_headings_preserve_numbered_steps_and_source_details(self):
        for heading in ("Workflow", "Steps", "wOrKfLoW", "STEPS"):
            with self.subTest(heading=heading):
                ir = parse_skill_text(
                    "---\nname: process\ndescription: Numbered process.\n---\n\n"
                    f"### {heading}\n"
                    "1) **Prepare output** — use the reviewed draft\n"
                    "1. Ask user for approval\n"
                )
                self.assertEqual(ir["ordered_steps"], [
                    "Prepare output — use the reviewed draft", "Ask user for approval",
                ])
                self.assertEqual(ir["ordered_step_details"], [
                    {"title": "Prepare output", "detail": "use the reviewed draft", "line": 7, "section": heading},
                    {"title": "Ask user for approval", "detail": "", "line": 8, "section": heading},
                ])

    def test_checklist_keeps_precedence_even_when_empty_or_after_process_sections(self):
        for checklist, expected in (
            ("## Checklist\n", []),
            ("## Verification Checklist\n- [ ] Existing check\n", ["Existing check"]),
            ("## Checklist\n1. Existing step\n", ["Existing step"]),
        ):
            with self.subTest(checklist=checklist):
                text = "## Workflow\n1. New step\n## Steps\n1. Another step\n" + checklist
                self.assertEqual(parse_skill_text(text)["ordered_steps"], expected)

    def test_process_heading_is_exact_and_direct_section_only(self):
        text = (
            "## Tools\n1. Tool inventory\n## Workflow notes\n1. Commentary\n"
            "## Workflow\n1. Prepare output\n### Notes\n1. Nested example\n"
            "## Verification\n1. Verify another example\n"
        )
        self.assertEqual(parse_skill_text(text)["ordered_steps"], ["Prepare output"])

    def test_empty_atx_heading_ends_the_process_section(self):
        ir = parse_skill_text("## Workflow\n1. Prepare output\n###\n1. Separate section\n")
        self.assertEqual(ir["ordered_steps"], ["Prepare output"])

    def test_fallback_ignores_bullets_and_nested_numbered_lists(self):
        for text, expected in (
            ("## Workflow\n-\n  1. Nested example\n", []),
            ("## Workflow\n1.\n   1. Nested example\n", []),
            ("## Workflow\n- Notes\n  1. Nested example\n", []),
            ("## Workflow\n+ Notes\n   1. Nested example\n", []),
            ("## Steps\n1. Prepare output\n   1. Nested detail\n2. Ask user for approval\n", ["Prepare output", "Ask user for approval"]),
            ("## Steps\n  1. Prepare output\n     1. Nested detail\n  2. Ask user for approval\n", ["Prepare output", "Ask user for approval"]),
            ("## Steps\n    1. Indented code\n", []),
            ("## Steps\n- Prepare output\n- [ ] Ask user for approval\n", []),
        ):
            with self.subTest(text=text):
                self.assertEqual(parse_skill_text(text)["ordered_steps"], expected)

    def test_backticks_in_an_info_string_do_not_hide_following_steps(self):
        ir = parse_skill_text(
            "## Workflow\n1. Prepare output\n```example```\n2. Ask user for approval\n"
        )
        self.assertEqual(ir["ordered_steps"], ["Prepare output", "Ask user for approval"])

    def test_fallback_ignores_matching_fenced_examples_without_changing_section(self):
        for fence in ("```", "~~~~", "````"):
            with self.subTest(fence=fence):
                text = (
                    f"{fence}markdown\n## Workflow\n1. Fenced example\n{fence}\n"
                    f"## Steps\n1. Prepare output\n{fence}\n2. Another example\n{fence}\n"
                    "2. Ask user for approval\n"
                )
                self.assertEqual(parse_skill_text(text)["ordered_steps"], ["Prepare output", "Ask user for approval"])

    def test_short_or_wrong_fence_does_not_end_a_fenced_example(self):
        for opening, wrong_close in (("````", "```"), ("~~~", "```"), ("```", "~~~")):
            with self.subTest(opening=opening, wrong_close=wrong_close):
                text = (
                    f"{opening}markdown\n{wrong_close}\n## Workflow\n1. Fenced example\n{opening}\n"
                    "## Steps\n1. Prepare output\n"
                )
                self.assertEqual(parse_skill_text(text)["ordered_steps"], ["Prepare output"])

    def test_unclosed_fence_remains_non_executable_through_end_of_input(self):
        self.assertEqual(parse_skill_text("~~~markdown\n## Workflow\n1. Fenced example\n")["ordered_steps"], [])

    def test_multiple_populated_process_sections_are_rejected_without_source_text(self):
        for second in ("Workflow", "Steps"):
            with self.subTest(second=second):
                with self.assertRaises(ValueError) as raised:
                    parse_skill_text(f"## Workflow\n1. Private first process\n## {second}\n1. Private second process\n")
                self.assertEqual(str(raised.exception), AMBIGUOUS_PROCESS)

    def test_empty_process_sections_do_not_create_ambiguity(self):
        ir = parse_skill_text("## Workflow\nFollow these steps.\n### Steps\n1. Prepare output\n## Workflow\nNo list here.\n")
        self.assertEqual(ir["ordered_steps"], ["Prepare output"])

    def test_compiled_process_reaches_a_durable_human_gate_before_its_successor(self):
        for heading in ("Workflow", "Steps"):
            with self.subTest(heading=heading), TemporaryDirectory() as temporary:
                ir = parse_skill_text(f"## {heading}\n1. Prepare output\n2. Ask user for approval\n3. Deliver output\n")
                workflow = compile_ir_to_workflow(ir)
                self.assertEqual(validate_workflow(workflow), [])
                review = summarize_skill_compile(ir, workflow)
                self.assertEqual(review["ordered_step_count"], 3)
                self.assertEqual(review["human_gate_count"], 1)
                self.assertNotIn("checklist_not_found", review["notices"])
                self.assertEqual(workflow["nodes"][2]["metadata"]["source"]["section"], heading)
                state_dir = Path(temporary) / "state"
                waiting = LocalExecutor(state_dir, storage="sqlite").run(workflow)
                self.assertEqual(waiting["status"], "waiting")
                self.assertNotIn("node_003_deliver_output", waiting["node_results"])
                completed = LocalExecutor(state_dir, storage="sqlite").resume(waiting["run_id"], approved=True)
                self.assertEqual(completed["status"], "completed")
                self.assertIn("node_003_deliver_output", completed["node_results"])
