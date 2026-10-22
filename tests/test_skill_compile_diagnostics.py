import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.parser import parse_skill_text
from tests import test_ui as ui_tests


VERSION = 'skill2workflow-skill-compile-diagnostic-0.1.0'
DUPLICATE = '---\nname: reviewed\ndescription: Synthetic example.\nname: private-value-canary\n---\n## Steps\n1. Review\n'


class SkillCompileDiagnosticTests(TestCase):
    def test_installed_browser_module_flag_requires_recovery_and_draft_ownership_suites(self):
        import subprocess
        from scripts.skill_compile_recovery_smoke import qualify
        original = subprocess.run
        commands = []

        def selected_run(command, **kwargs):
            if command[0] == 'node':
                commands.append(command)
                return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
            return original(command, **kwargs)

        with patch('scripts.skill_compile_recovery_smoke.subprocess.run', side_effect=selected_run):
            self.assertTrue(qualify(browser_module_tests=True)['browser_module_verified'])
        self.assertEqual(len(commands), 1)
        self.assertIn(str(Path(__file__).resolve().parent / 'test_skill_compile_recovery.cjs'), commands[0])
        self.assertIn(str(Path(__file__).resolve().parent / 'test_draft_load_ownership.cjs'), commands[0])

    def test_installed_gate_requires_complete_diagnostic_legacy_cli_and_module_evidence(self):
        from scripts import package_smoke
        complete = {'ok': True, 'installed': True, 'cases_verified': 10,
                    'diagnostic_cases_verified': 4, 'legacy_cases_verified': 2,
                    'cli_cases_verified': 2, 'module_served': True}
        for result in (complete, {}, dict(complete, cases_verified=9), dict(complete, diagnostic_cases_verified=3),
                       dict(complete, legacy_cases_verified=0), dict(complete, cli_cases_verified=0), dict(complete, module_served=False),
                       dict(complete, module_served=1), dict(complete, installed=1), dict(complete, ok=1)):
            with patch('scripts.package_smoke._run', return_value=json.dumps(result)):
                if result is complete:
                    self.assertTrue(package_smoke._qualify_installed_skill_compile_recovery(Path('/repo'), Path('/cli'), Path('/isolated')))
                else:
                    with self.assertRaises(RuntimeError):
                        package_smoke._qualify_installed_skill_compile_recovery(Path('/repo'), Path('/cli'), Path('/isolated'))
    def test_diagnostics_do_not_change_comment_only_frontmatter_acceptance(self):
        for header in ('', '\t# ignored', '  # ignored\n\t# ignored'):
            self.assertEqual(parse_skill_text('---\n' + header + '\n---\n## Steps\n1. Review')['metadata'], {})
    def test_frontmatter_error_has_safe_reason_and_original_line_without_changing_valueerror_text(self):
        for text, code, line in [
            (DUPLICATE, 'frontmatter_duplicate_key', 4),
            (DUPLICATE.replace('\n', '\r\n'), 'frontmatter_duplicate_key', 4),
            ('---\nmetadata:\n  name: a\n  name: private-value-canary\n---', 'frontmatter_duplicate_key', 4),
            ('---\nname: reviewed\ndescription: "private-value-canary\n---', 'frontmatter_invalid', 3),
            ('---\nname: reviewed\ndescription: *private-value-canary\n---', 'frontmatter_unsupported', 3),
            ('---\nmetadata: {name: private-value-canary}\n---', 'frontmatter_unsupported', 2),
        ]:
            with self.subTest(code=code, line=line):
                with self.assertRaises(ValueError) as caught:
                    parse_skill_text(text)
                self.assertEqual(str(caught.exception), 'Invalid SKILL.md frontmatter')
                self.assertEqual(getattr(caught.exception, 'code', None), code)
                self.assertEqual(getattr(caught.exception, 'line', None), line)
                self.assertNotIn('private-value-canary', str(caught.exception))

    def test_cli_names_the_location_and_next_edit_without_echoing_source(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'SKILL.md'
            source.write_text(DUPLICATE, encoding='utf-8')
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(['compile', str(source)]), 1)
            self.assertEqual(stdout.getvalue(), '')
            self.assertIn('line 4', stderr.getvalue())
            self.assertIn('one declaration', stderr.getvalue())
            self.assertNotIn('private-value-canary', stderr.getvalue())
            self.assertNotIn(directory, stderr.getvalue())

    def post(self, text, diagnostics=None):
        return ui_tests.UiTests._post_local_skill_compile(self, text, diagnostics)

    def test_api_diagnostic_is_explicit_opt_in_and_legacy_error_is_unchanged(self):
        for flag in (None, False):
            status, raw = self.post(DUPLICATE, flag)
            self.assertEqual(status, 400)
            self.assertEqual(json.loads(raw), {'error': 'skill compile rejected'})
        status, raw = self.post(DUPLICATE, True)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw), {'error': 'skill compile rejected', 'diagnostic': {
            'schema_version': VERSION, 'code': 'frontmatter_duplicate_key', 'line': 4}})
        self.assertLess(len(raw), 1024)
        self.assertNotIn(b'private-value-canary', raw)

    def test_api_rejects_non_boolean_opt_in_and_never_classifies_invalid_envelopes(self):
        for flag in (1, 'private-value-canary', [], {}):
            status, raw = self.post(DUPLICATE, flag)
            self.assertEqual(status, 400)
            self.assertEqual(json.loads(raw), {'error': 'skill compile body is malformed'})

    def test_opt_in_success_is_identical_and_generic_errors_do_not_invent_a_cause(self):
        text = '---\nname: reviewed\n---\n## Steps\n1. Review\n'
        legacy = self.post(text)
        opted = self.post(text, True)
        self.assertEqual(legacy, opted)
        with patch('skill2workflow.ui.parse_skill_text', side_effect=ValueError('private-message-canary')):
            status, raw = self.post(text, True)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw)['diagnostic'], {'schema_version': VERSION, 'code': 'skill_invalid', 'line': None})
        self.assertNotIn(b'private-message-canary', raw)

    def test_malformed_internal_evidence_cannot_escape_the_finite_diagnostic_contract(self):
        from skill2workflow.frontmatter import FrontmatterError, skill_compile_diagnostic
        error = FrontmatterError('frontmatter_invalid', 3)
        for code, line in [('private-code-canary', 3), (['private-code-canary'], 3), ('frontmatter_invalid', True), ('frontmatter_invalid', 'private-line-canary'), ('frontmatter_invalid', -2)]:
            error.code, error.line = code, line
            result = skill_compile_diagnostic(error)
            self.assertNotIn('private-', json.dumps(result))
            self.assertTrue(result['line'] is None or type(result['line']) is int)
        self.assertEqual(skill_compile_diagnostic(ValueError('private-message-canary')), {
            'schema_version': VERSION, 'code': 'skill_invalid', 'line': None})
