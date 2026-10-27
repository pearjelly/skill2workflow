from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.compiler import compile_ir_to_workflow, summarize_skill_compile, validate_workflow
from skill2workflow.executor import LocalExecutor
from skill2workflow.parser import parse_skill_text


AMBIGUOUS_PROCESS = (
    "SKILL.md has multiple Workflow or Steps sections; "
    "use one process section or an explicit Checklist"
)


class ProcessStepTests(TestCase):
    def test_indented_fenced_checklist_examples_are_not_steps(self):
        for fence in ('    ~~~', '    ```', '\t~~~'):
            with self.subTest(fence=fence):
                text = ('## Checklist\n1. Prepare output\n' + fence + 'markdown\n'
                        '    2. Run private example\n' + fence + '\n'
                        '2. Ask user for approval\n3. Deliver output\n')
                ir = parse_skill_text(text)
                self.assertEqual(ir['ordered_steps'],
                                 ['Prepare output', 'Ask user for approval', 'Deliver output'])
                self.assertEqual([step['line'] for step in ir['ordered_step_details']], [2, 6, 7])
                self.assertNotIn('private example', str(compile_ir_to_workflow(ir)))

    def test_blockquote_fenced_checklist_does_not_override_real_process(self):
        text = ('> ```markdown\n> ## Checklist\n> 1. Run private example\n'
                '> <HARD-GATE>private example</HARD-GATE>\n> ```\n'
                '## Workflow\n1. Prepare output\n2. Ask user for approval\n')
        ir = parse_skill_text(text)
        self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Ask user for approval'])
        self.assertEqual(ir['tool_hints'], [])
        self.assertEqual(ir['hard_gates'], [])
        self.assertNotIn('private example', str(compile_ir_to_workflow(ir)))

    def test_list_contained_fences_exclude_example_declarations_and_hints(self):
        text = ('## Checklist\n1. Prepare output\n- ```markdown\n'
                '  1. Run private example <!-- skill2workflow: human_gate -->\n'
                '  <!-- skill2workflow: workflow_version private-example -->\n'
                '  <!-- skill2workflow: input_schema {"private":"example"} -->\n'
                '  <HARD-GATE>private example</HARD-GATE>\n  ```\n'
                '2. Review <!-- skill2workflow: human_gate -->\n3. Deliver output\n')
        ir = parse_skill_text(text)
        self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Review', 'Deliver output'])
        self.assertEqual(ir['hard_gates'], [])
        self.assertEqual(ir['tool_hints'], [])
        self.assertNotIn('input_schema', ir)
        self.assertNotIn('workflow_version', ir)
        workflow = compile_ir_to_workflow(ir)
        self.assertEqual([node['type'] for node in workflow['nodes']],
                         ['start', 'step', 'human_gate', 'step', 'failure', 'end'])
        self.assertNotIn('private example', str(workflow))

    def test_unclosed_nested_fence_refuses_instead_of_excluding_the_remainder(self):
        with self.assertRaisesRegex(ValueError, 'unclosed.*line 3'):
            parse_skill_text('## Checklist\n1. Prepare output\n    ~~~markdown\n'
                             '    2. Run private example\n2. Deliver output\n')

    def test_nested_closers_cannot_end_a_top_level_fence(self):
        text = ('## Checklist\n1. Prepare output\n~~~markdown\n'
                '    ~~~\n2. Run private example\n~~~\n2. Deliver output\n')
        ir = parse_skill_text(text)
        self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Deliver output'])
        self.assertNotIn('private example', str(compile_ir_to_workflow(ir)))

    def test_wrong_container_cannot_close_a_fenced_example(self):
        text = ('## Checklist\n1. Prepare output\n> ~~~markdown\n'
                '~~~\n2. Run private example\n> ~~~\n2. Deliver output\n')
        ir = parse_skill_text(text)
        self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Deliver output'])
        self.assertNotIn('private example', str(compile_ir_to_workflow(ir)))

    def test_wrong_nested_indent_and_quote_position_cannot_close_a_fence(self):
        for opening, wrong, closing in (
            ('    ~~~', '  ~~~', '    ~~~'),
            ('> ~~~', '  > ~~~', '> ~~~'),
            ('- > ~~~', '> ~~~', '  > ~~~'),
        ):
            with self.subTest(opening=opening):
                text = ('## Checklist\n1. Prepare output\n' + opening + 'markdown\n'
                        + wrong + '\n2. Run private example\n' + closing
                        + '\n2. Deliver output\n')
                ir = parse_skill_text(text)
                self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Deliver output'])
                self.assertNotIn('private example', str(compile_ir_to_workflow(ir)))

    def test_nested_http_example_never_runs_before_or_after_real_approval(self):
        text = ('## Checklist\n1. Prepare output\n    ~~~~markdown\n'
                '    2. Send <!-- skill2workflow: http {"request":{"method":"POST",'
                '"url":"https://example.invalid/private"}} -->\n    ~~~~\n'
                '2. Review <!-- skill2workflow: human_gate -->\n3. Deliver output\n')
        with TemporaryDirectory() as temporary, patch('skill2workflow.connectors._open_http_request') as transport:
            ir = parse_skill_text(text)
            workflow = compile_ir_to_workflow(ir)
            self.assertEqual(validate_workflow(workflow), [])
            self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Review', 'Deliver output'])
            self.assertNotIn('example.invalid', str(workflow))
            executor = LocalExecutor(Path(temporary) / 'state', storage='sqlite')
            waiting = executor.run(workflow)
            self.assertEqual(waiting['status'], 'waiting')
            transport.assert_not_called()
            completed = executor.resume(waiting['run_id'], approved=True)
            self.assertEqual(completed['status'], 'completed')
            transport.assert_not_called()

    def test_checklist_fences_exclude_example_steps_and_preserve_real_source_lines(self):
        for opening, wrong in (("~~~~", "```"), ("````", "```"), ("```", "~~~")):
            with self.subTest(opening=opening):
                text = ("## Checklist\n1. Prepare output\n" + opening + "markdown\n"
                        + wrong + "\n2. Run private example\n" + opening
                        + "\n2. Ask user for approval\n3. Deliver output\n")
                ir = parse_skill_text(text)
                self.assertEqual(ir['ordered_steps'], [
                    'Prepare output', 'Ask user for approval', 'Deliver output'])
                self.assertEqual([step['line'] for step in ir['ordered_step_details']], [2, 7, 8])
                workflow = compile_ir_to_workflow(ir)
                self.assertEqual([node['type'] for node in workflow['nodes']],
                                 ['start', 'step', 'human_gate', 'step', 'failure', 'end'])
                self.assertNotIn('private example', str(workflow))

    def test_fenced_checklist_heading_does_not_override_real_workflow(self):
        text = ('~~~~markdown\n## Checklist\n1. Fenced example\n~~~~\n'
                '## Workflow\n1. Prepare output\n2. Ask user for approval\n')
        ir = parse_skill_text(text)
        self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Ask user for approval'])
        self.assertEqual(ir['ordered_step_details'][0]['line'], 6)

    def test_fenced_guidance_does_not_create_gates_or_hints(self):
        text = ('## Checklist\n1. Prepare output\n~~~~markdown\n'
                '<HARD-GATE>Private example approval</HARD-GATE>\n'
                'Run: private example tool; verify private example\n~~~~\n'
                '2. Deliver output\n')
        ir = parse_skill_text(text)
        self.assertEqual(ir['hard_gates'], [])
        self.assertEqual(ir['tool_hints'], [])
        self.assertEqual(ir['human_gates'], [])
        self.assertEqual(ir['verification_rules'], [])
        workflow = compile_ir_to_workflow(ir)
        self.assertEqual(workflow['guards'], [])
        self.assertNotIn('private example', str(workflow))

    def test_unclosed_checklist_fence_cannot_add_steps_or_hints(self):
        with self.assertRaisesRegex(ValueError, 'unclosed.*line 3'):
            parse_skill_text('## Checklist\n1. Prepare output\n~~~markdown\n'
                             '2. Ask user for approval\nRun: private example\n')

    def test_invalid_backtick_info_does_not_hide_checklist_steps(self):
        ir = parse_skill_text('## Checklist\n1. Prepare output\n```example```\n'
                              '2. Ask user for approval\n')
        self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Ask user for approval'])

    def test_fenced_checklist_annotations_never_become_runtime_steps(self):
        text = ('## Checklist\n1. Prepare output\n~~~~markdown\n'
                '2. Send <!-- skill2workflow: http {"request":{"method":"POST",'
                '"url":"https://example.invalid/private"}} -->\n'
                '<HARD-GATE>Example only</HARD-GATE>\n~~~~\n'
                '2. Review <!-- skill2workflow: human_gate -->\n3. Deliver output\n')
        with TemporaryDirectory() as temporary, patch('skill2workflow.connectors._open_http_request') as transport:
            ir = parse_skill_text(text)
            workflow = compile_ir_to_workflow(ir)
            self.assertEqual(validate_workflow(workflow), [])
            self.assertEqual(ir['ordered_steps'], ['Prepare output', 'Review', 'Deliver output'])
            self.assertEqual(workflow['guards'], [])
            self.assertNotIn('example.invalid', str(workflow))
            executor = LocalExecutor(Path(temporary) / 'state', storage='sqlite')
            waiting = executor.run(workflow)
            self.assertEqual(waiting['status'], 'waiting')
            transport.assert_not_called()
            completed = executor.resume(waiting['run_id'], approved=True)
            self.assertEqual(completed['status'], 'completed')
            transport.assert_not_called()

    def test_sections_keep_fenced_content_without_creating_fenced_headings(self):
        text = ('## Checklist\n1. Prepare\n~~~~markdown\n## Fenced heading\n'
                '1. Example\n~~~~\n2. Deliver\n')
        ir = parse_skill_text(text)
        self.assertNotIn('Fenced heading', ir['sections'])
        self.assertIn('## Fenced heading\n1. Example', ir['sections']['Checklist'])
        self.assertEqual(ir['ordered_steps'], ['Prepare', 'Deliver'])

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

    def test_unclosed_fence_refuses_before_any_draft_is_created(self):
        with self.assertRaisesRegex(ValueError, 'unclosed.*line 1'):
            parse_skill_text("~~~markdown\n## Workflow\n1. Fenced example\n")

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
