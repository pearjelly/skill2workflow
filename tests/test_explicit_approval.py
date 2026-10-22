import json
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow
from skill2workflow.cli import main
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.parser import parse_skill_text
from skill2workflow.quickstart import initialize_quickstart_workspace


MARKER = '<!-- skill2workflow: human_gate -->'


class ExplicitApprovalTests(TestCase):
    def test_cli_compiles_explicit_chinese_approval_and_refuses_bad_annotation_without_output(self):
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / 'SKILL.md'
            source.write_text(f'## Steps\n1. 等待负责人审核 {MARKER}\n', encoding='utf-8')
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(['compile', str(source), '--review']), 0)
            compiled = json.loads(output.getvalue())
            self.assertEqual(compiled['review']['human_gate_count'], 1)
            self.assertEqual(compiled['workflow']['nodes'][1]['title'], '等待负责人审核')
            source.write_text('## Steps\n1. 等待 <!-- skill2workflow: unknown -->\n', encoding='utf-8')
            target = Path(temporary) / 'workflow.json'
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertNotEqual(main(['compile', str(source), '-o', str(target)]), 0)
            self.assertFalse(target.exists())

    def test_selected_steps_preserve_explicit_type_and_clean_source_text(self):
        for heading in ('Checklist', 'Workflow', 'Steps'):
            with self.subTest(heading=heading):
                ir = parse_skill_text(f'## {heading}\n1. **等待负责人审核** — 检查草稿 {MARKER}\n')
                step = ir['ordered_step_details'][0]
                self.assertEqual(step['node_type'], 'human_gate')
                self.assertEqual(step['title'], '等待负责人审核')
                self.assertEqual(step['detail'], '检查草稿')
                self.assertEqual(step['line'], 2)
                self.assertNotIn('skill2workflow:', str(ir['ordered_steps']))
                workflow = compile_ir_to_workflow(ir)
                self.assertEqual(validate_workflow(workflow), [])
                node = workflow['nodes'][1]
                self.assertEqual(node['type'], 'human_gate')
                self.assertEqual(node['action']['prompt'], '等待负责人审核 — 检查草稿')
                self.assertEqual(node['on_failure'], 'failure')
                self.assertNotIn('<!--', json.dumps(workflow))
                unmarked = compile_ir_to_workflow(parse_skill_text(
                    f'## {heading}\n1. **等待负责人审核** — 检查草稿\n'
                ))
                self.assertEqual(node['id'], unmarked['nodes'][1]['id'])

    def test_bad_or_unattached_reserved_annotations_are_rejected(self):
        cases = [
            f'## Workflow\n1. 等待 {MARKER} {MARKER}\n',
            '## Workflow\n1. 等待 <!-- skill2workflow: human_gte -->\n',
            '## Workflow\n1. 等待 <!-- skill2workflow: human_gate\n',
            f'## Workflow\n1. {MARKER}\n',
            f'## Workflow\n1. 等待 {MARKER} trailing\n',
            f'## Notes\n等待 {MARKER}\n',
            f'## Workflow\n1. 等待\n   1. 嵌套 {MARKER}\n',
            f'## Workflow\n1. 等待 {MARKER}\n## Checklist\n',
            f'## Checklist\n~~~\n1. 示例 {MARKER}\n~~~\n',
            '## Steps\n1. 等待 <!-- Skill2Workflow: human_gate -->\n',
        ]
        for text in cases:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
                parse_skill_text(text)

    def test_fenced_annotations_are_examples_and_unmarked_steps_stay_compatible(self):
        ir = parse_skill_text(f'```markdown\n1. 示例 {MARKER}\n```\n## Steps\n1. 等待负责人审核\n')
        self.assertNotIn('node_type', ir['ordered_step_details'][0])
        self.assertEqual(compile_ir_to_workflow(ir)['nodes'][1]['type'], 'step')

    def test_explicit_ir_type_precedes_keywords_and_rejects_unknown_types(self):
        ir = parse_skill_text(f'## Steps\n1. Verify output {MARKER}\n')
        self.assertEqual(compile_ir_to_workflow(ir)['nodes'][1]['type'], 'human_gate')
        ir['ordered_step_details'][0]['node_type'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'Unsupported explicit Skill step type'):
            compile_ir_to_workflow(ir)

    def test_chinese_custom_quickstart_durably_approves_or_rejects(self):
        for approved, status in ((True, 'completed'), (False, 'failed')):
            with self.subTest(approved=approved), TemporaryDirectory() as temporary:
                parent = Path(temporary)
                source = parent / 'SKILL.md'
                source.write_text(f'---\nname: explicit-review\n---\n## Workflow\n1. 整理草稿\n2. 等待负责人审核 {MARKER}\n3. 输出结果\n', encoding='utf-8')
                root = parent / 'service'
                result = initialize_quickstart_workspace(root, port=0, skill_path=source)
                self.assertEqual(result['run_status'], 'waiting')
                control = LocalControlPlane(root / 'state', storage='sqlite')
                waiting = control.get_run(result['run_id'])
                workflow = json.loads((root / 'example/workflow.json').read_text())
                successor = workflow['nodes'][3]['id']
                self.assertNotIn(successor, waiting['node_results'])
                resumed = control.resume_published_run(result['run_id'], approved=approved)
                self.assertEqual(resumed['status'], status)
                self.assertEqual(successor in resumed['node_results'], approved)
