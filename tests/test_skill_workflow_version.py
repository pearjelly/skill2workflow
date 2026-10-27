import copy
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.authoring_artifacts import create_authoring_artifacts, preflight_authoring_repair, repair_authoring_artifacts, verify_authoring_artifacts
from skill2workflow.cli import main
from skill2workflow.compiler import compile_ir_to_workflow
from skill2workflow.parser import parse_skill_text
from tests import test_ui as ui_tests


ERROR = 'Invalid Skill workflow version declaration'
SOURCE = '---\nname: versioned-review\nmetadata:\n  version: private-metadata-canary\n---\n<!-- skill2workflow: workflow_version 0.2.0-rc.1 -->\n## Steps\n1. Review <!-- skill2workflow: human_gate -->\n2. Deliver\n'


class SkillWorkflowVersionTests(TestCase):
    def test_installed_gate_requires_every_versioned_iteration_check(self):
        from scripts import package_smoke
        checks = {name: True for name in ('compile', 'artifacts', 'repair', 'bundles', 'publication',
                                         'immutable_conflict', 'pinned_runs', 'quickstart', 'ui', 'invalid_source')}
        complete = {'ok': True, 'installed': True, 'checks': checks}
        cases = [complete, {}, dict(complete, installed=False), dict(complete, installed=1), dict(complete, ok=1)]
        cases += [dict(complete, checks=dict(checks, **{name: False})) for name in checks]
        cases += [dict(complete, checks=dict(checks, compile=1)), dict(complete, checks={})]
        for result in cases:
            with patch('scripts.package_smoke._run', return_value=json.dumps(result)):
                if result is complete:
                    self.assertTrue(package_smoke._qualify_installed_skill_versions(Path('/repo'), Path('/cli'), Path('/isolated')))
                else:
                    with self.assertRaises(RuntimeError):
                        package_smoke._qualify_installed_skill_versions(Path('/repo'), Path('/cli'), Path('/isolated'))

    def test_input_contract_and_version_declarations_coexist_without_inference_or_line_shifts(self):
        marker = '<!-- skill2workflow: workflow_version approval-verify -->'
        text = '<!-- skill2workflow: input_schema {"type":"object","properties":{"id":{"type":"string"}}} -->\n' + marker + '\n## Checklist\n1. Deliver\n'
        ir = parse_skill_text(text)
        workflow = compile_ir_to_workflow(ir)
        self.assertEqual(workflow['workflow']['version'], 'approval-verify')
        self.assertEqual(workflow['nodes'][1]['type'], 'step')
        self.assertEqual(workflow['nodes'][1]['metadata']['source']['line'], 4)
        self.assertEqual(workflow['input_schema']['properties']['id']['type'], 'string')
        self.assertEqual(ir['human_gates'], [])
        self.assertEqual(ir['verification_rules'], [])

    def test_custom_quickstart_uses_declared_version_at_the_durable_gate(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'SKILL.md'
            source.write_text(SOURCE, encoding='utf-8')
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(['quickstart', '--skill', str(source), '--root', str(root / 'runtime')]), 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result['workflow_version'], '0.2.0-rc.1')
            self.assertEqual(result['run_status'], 'waiting')
            from skill2workflow.control_plane import LocalControlPlane
            control = LocalControlPlane(root / 'runtime' / 'state', storage='sqlite')
            self.assertEqual(control.get_run(result['run_id'])['workflow_version'], '0.2.0-rc.1')

    def test_explicit_source_version_preserves_identity_lines_and_non_authoritative_metadata(self):
        ir = parse_skill_text(SOURCE)
        before = copy.deepcopy(ir)
        workflow = compile_ir_to_workflow(ir)
        self.assertEqual(ir, before)
        self.assertEqual(ir['workflow_version'], '0.2.0-rc.1')
        self.assertEqual(workflow['workflow']['version'], '0.2.0-rc.1')
        self.assertEqual(workflow['workflow']['id'], 'workflow_versioned_review')
        self.assertEqual(workflow['schema_version'], '0.1.0')
        self.assertEqual(workflow['nodes'][1]['metadata']['source']['line'], 8)
        self.assertEqual(workflow['nodes'][1]['type'], 'human_gate')
        self.assertNotIn('workflow_version', json.dumps(workflow['nodes']))
        self.assertNotIn('private-metadata-canary', json.dumps(workflow))
        implicit = compile_ir_to_workflow(parse_skill_text(SOURCE.replace('<!-- skill2workflow: workflow_version 0.2.0-rc.1 -->', '')))
        self.assertEqual(implicit['workflow']['version'], '0.1.0')

    def test_supported_tokens_and_crlf_keep_original_source_mapping(self):
        for version in ('1', 'v2.1_0-rc.1', 'A' * 128):
            text = SOURCE.replace('0.2.0-rc.1', version).replace('\n', '\r\n')
            workflow = compile_ir_to_workflow(parse_skill_text(text))
            self.assertEqual(workflow['workflow']['version'], version)
            self.assertEqual(workflow['nodes'][1]['metadata']['source']['line'], 8)
        padded = SOURCE.replace('<!-- skill2workflow: workflow_version 0.2.0-rc.1 -->',
                                '   <!-- skill2workflow: workflow_version 0.2.0-rc.1 -->\t ')
        self.assertEqual(compile_ir_to_workflow(parse_skill_text(padded))['workflow']['version'], '0.2.0-rc.1')
        unrelated = '---\nname: review\nversion: 9.9.9\nworkflow_version: 8.8.8\n---\n## Steps\n1. Review\n'
        self.assertEqual(compile_ir_to_workflow(parse_skill_text(unrelated))['workflow']['version'], '0.1.0')

    def test_invalid_duplicate_and_misplaced_declarations_refuse_without_source_echo(self):
        marker = '<!-- skill2workflow: workflow_version 0.2.0-rc.1 -->'
        bad = ['', ' ', '../private-path-canary', '.hidden', 'a/b', 'a\\b', '1+build', '中文', 'a' * 129, '"private-value-canary"', '0.2.0 --> <!-- injected']
        forms = [SOURCE.replace('0.2.0-rc.1', value) for value in bad]
        forms += [SOURCE.replace(marker, marker + '\n' + marker), SOURCE.replace(marker, 'prefix ' + marker),
                  SOURCE.replace(marker, '').replace('1. Review', '1. Review ' + marker),
                  SOURCE.replace(marker, '    ' + marker), SOURCE.replace(marker, marker.replace('workflow_version', 'WORKFLOW_VERSION')),
                  SOURCE.replace(marker, marker.replace(' -->', '-->')), SOURCE.replace(marker, marker + ' suffix')]
        for text in forms:
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as caught:
                    parse_skill_text(text)
                self.assertEqual(str(caught.exception), ERROR)

    def test_fenced_declarations_are_examples_not_deployment_intent(self):
        marker = '<!-- skill2workflow: workflow_version 9.9.9 -->'
        for opening, closing in [('```markdown', '```'), ('~~~~', '~~~~')]:
            text = '---\nname: review\n---\n## Steps\n1. Review\n\n' + opening + '\n' + marker + '\n' + closing
            ir = parse_skill_text(text)
            self.assertNotIn('workflow_version', ir)
            self.assertEqual(compile_ir_to_workflow(ir)['workflow']['version'], '0.1.0')
        with self.assertRaisesRegex(ValueError, 'unclosed.*line 7'):
            parse_skill_text('---\nname: review\n---\n## Steps\n1. Review\n\n```\n' + marker + '\n')

    def test_compiler_revalidates_untrusted_explicit_ir_without_coercion(self):
        baseline = parse_skill_text('## Steps\n1. Review\n')
        for value in (None, True, 2, [], {}, '', '../private-path-canary', 'a' * 129):
            ir = dict(baseline, workflow_version=value)
            with self.assertRaises(ValueError) as caught:
                compile_ir_to_workflow(ir)
            self.assertEqual(str(caught.exception), ERROR)

    def test_cli_and_local_helper_compile_the_declared_version_with_unchanged_review_shape(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'SKILL.md'
            source.write_text(SOURCE, encoding='utf-8')
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(['compile', str(source), '--review']), 0)
            compiled = json.loads(stdout.getvalue())
            self.assertEqual(compiled['workflow']['workflow']['version'], '0.2.0-rc.1')
            self.assertEqual(compiled['review']['schema_version'], 'skill2workflow-skill-compile-review-0.1.0')
            status, raw = ui_tests.UiTests._post_local_skill_compile(self, SOURCE)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)['workflow']['workflow']['version'], '0.2.0-rc.1')
            status, raw = ui_tests.UiTests._post_local_skill_compile(self, SOURCE.replace('0.2.0-rc.1', '../private-value-canary'))
            self.assertEqual(status, 400)
            self.assertEqual(json.loads(raw), {'error': 'skill compile rejected'})

    def test_export_and_backed_up_repair_keep_source_version_and_valid_manifest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, destination, backup = root / 'SKILL.md', root / 'set', root / 'backup'
            source.write_text(SOURCE, encoding='utf-8')
            self.assertEqual(create_authoring_artifacts(source, destination)['workflow_version'], '0.2.0-rc.1')
            before = {p.name: p.read_bytes() for p in destination.iterdir()}
            self.assertEqual(preflight_authoring_repair(source, destination, backup)['workflow_version'], '0.2.0-rc.1')
            self.assertFalse(backup.exists())
            self.assertEqual({p.name: p.read_bytes() for p in destination.iterdir()}, before)
            (destination / 'workflow.json').write_text('{}', encoding='utf-8')
            self.assertEqual(repair_authoring_artifacts(source, destination, backup)['workflow_version'], '0.2.0-rc.1')
            self.assertTrue(verify_authoring_artifacts(destination)['valid'])
            self.assertEqual((backup / 'workflow.json').read_text(), '{}')

    def test_invalid_source_creates_no_compile_export_or_quickstart_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'SKILL.md'
            source.write_text(SOURCE.replace('0.2.0-rc.1', '../private-value-canary'), encoding='utf-8')
            output = root / 'workflow.json'
            for command in (['compile', str(source), '-o', str(output)],
                            ['authoring-export', str(source), '--output-dir', str(root / 'set')],
                            ['quickstart', '--skill', str(source), '--root', str(root / 'runtime')]):
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(main(command), 1)
                self.assertEqual(stdout.getvalue(), '')
                self.assertEqual(stderr.getvalue().strip(), ERROR)
            self.assertEqual(list(root.iterdir()), [source])
            source.write_text(SOURCE, encoding='utf-8')
            destination, backup = root / 'set', root / 'backup'
            create_authoring_artifacts(source, destination)
            before = {p.name: p.read_bytes() for p in destination.iterdir()}
            source.write_text(SOURCE.replace('0.2.0-rc.1', '../private-value-canary'), encoding='utf-8')
            for operation in (preflight_authoring_repair, repair_authoring_artifacts):
                with self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                    operation(source, destination, backup)
                self.assertFalse(backup.exists())
                self.assertEqual({p.name: p.read_bytes() for p in destination.iterdir()}, before)
