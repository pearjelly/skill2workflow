import argparse
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from tests.test_cli import _approval_workflow


class CliStorageDefaultTests(TestCase):
    def test_every_storage_option_defaults_to_sqlite(self):
        captured = []

        def inspect_parser(parser, *_args, **_kwargs):
            captured.append(parser)
            raise SystemExit(0)

        with patch.object(argparse.ArgumentParser, 'parse_args', autospec=True, side_effect=inspect_parser):
            with self.assertRaises(SystemExit):
                main(['--help'])
        subcommands = next(action.choices for action in captured[0]._actions
                           if isinstance(action, argparse._SubParsersAction))
        defaults = {name: parser.get_default('storage') for name, parser in subcommands.items()
                    if any(action.dest == 'storage' for action in parser._actions)}
        self.assertGreater(len(defaults), 20)
        self.assertEqual(set(defaults.values()), {'sqlite'}, defaults)

    def test_default_sqlite_supports_publish_trigger_resume_and_inspection(self):
        self._local_lifecycle([])

    def test_explicit_json_preserves_existing_local_lifecycle(self):
        self._local_lifecycle(['--storage', 'json'])

    def _local_lifecycle(self, storage_args):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / 'state'
            workflow = root / 'workflow.json'
            workflow.write_text(json.dumps(_approval_workflow()), encoding='utf-8')

            def command(args):
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main([*args, '--state-dir', str(state_dir), *storage_args]), 0)
                return json.loads(output.getvalue())

            command(['publish', str(workflow)])
            triggered = command(['trigger', 'workflow_demo', '--version', '0.1.0',
                                 '--idempotency-key', 'storage-default'])
            run_id = triggered['run_id']
            self.assertEqual(command(['control-run', run_id])['status'], 'waiting')
            self.assertEqual(command(['resume-published', run_id])['status'], 'completed')
            self.assertEqual(command(['show', run_id])['status'], 'completed')
            self.assertTrue(command(['runs']))
            self.assertTrue(command(['audit']))
            sqlite_expected = not storage_args
            self.assertEqual((state_dir / 'control.sqlite3').exists(), sqlite_expected)
            self.assertEqual((state_dir / 'runs.sqlite3').exists(), sqlite_expected)
            self.assertEqual((state_dir / 'runs' / (run_id + '.json')).exists(), not sqlite_expected)
