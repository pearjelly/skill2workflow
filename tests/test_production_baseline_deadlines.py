import contextlib
import io
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from unittest import TestCase
from unittest.mock import Mock, patch

from scripts import production_baseline_smoke as baseline


ROOT = Path(__file__).resolve().parents[1]


class BaselineDeadlineTests(TestCase):
    def test_default_runner_receives_only_remaining_suite_budget(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(baseline.time, 'monotonic', side_effect=[0, 0, 599.75] + [600] * 17), \
             patch.object(baseline, '_run_command', return_value=(0, False)) as runner:
            result = baseline.run_baseline(Path(temporary) / 'baseline')
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(runner.call_args_list[0].kwargs, {'timeout_seconds': 180, 'suite_deadline': 600})
        self.assertEqual(runner.call_args_list[1].kwargs, {'timeout_seconds': .25, 'suite_deadline': 600})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['check_count'], 19)
        self.assertEqual(result['passed_count'], 2)
        self.assertTrue(all(item == {'name': item['name'], 'status': 'skipped', 'reason': 'suite_timeout'}
                            for item in result['checks'][2:]))
        guide = (ROOT / 'docs/production-baseline-evidence.md').read_text(encoding='utf-8')
        for phrase in ('600-second monotonic budget', 'remaining suite budget', 'five seconds',
                       'not Windows', 'not an absolute wall-clock guarantee',
                       'preserves the owner-only work directory'):
            self.assertIn(phrase, guide)

    def test_exhausted_budget_admits_no_subprocess(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(baseline.time, 'monotonic', side_effect=[0] + [600] * 19), \
             patch.object(baseline, '_run_command') as runner:
            result = baseline.run_baseline(Path(temporary) / 'baseline')
        runner.assert_not_called()
        self.assertEqual(result['passed_count'], 0)
        self.assertEqual(result['check_count'], 19)
        self.assertEqual(result['status'], 'failed')
        with patch.object(baseline.subprocess, 'Popen') as launch:
            for budget in (0, -1, float('nan'), float('inf')):
                self.assertEqual(baseline._run_command(['fixed'], ROOT, timeout_seconds=budget), (124, True))
        launch.assert_not_called()
        with patch.object(baseline.time, 'monotonic', return_value=600.1), \
             patch.object(baseline.subprocess, 'Popen') as launch:
            self.assertEqual(baseline._run_command(['fixed'], ROOT, timeout_seconds=.25,
                                                  suite_deadline=600), (124, True))
        launch.assert_not_called()

    def test_success_nonzero_and_short_timeout_preserve_compact_verdicts(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(baseline._run_command([sys.executable, '-c', 'raise SystemExit(7)'], ROOT), (7, False))
            self.assertEqual(baseline._run_command([sys.executable, '-c', 'print("synthetic-private-canary")'], ROOT), (0, False))
            started = time.monotonic()
            self.assertEqual(baseline._run_command([sys.executable, '-c', 'import time; time.sleep(30)'], ROOT,
                                                  timeout_seconds=.05), (124, True))
            self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(output.getvalue(), '')

    def test_timed_out_parent_cannot_leave_its_same_group_listener_running(self):
        child_code = '''import pathlib,socket,sys
s=socket.socket();s.bind(('127.0.0.1',0));s.listen()
pathlib.Path(sys.argv[1]).write_text(str(s.getsockname()[1]))
c,_=s.accept();c.recv(16);c.sendall(b'owned-child-canary');c.recv(64);c.close();s.close()
'''
        parent_code = 'import subprocess,sys; subprocess.Popen([sys.executable,"-c",sys.argv[1],sys.argv[2]]).wait()'
        with tempfile.TemporaryDirectory() as temporary:
            ready = Path(temporary) / 'port'
            real_popen = subprocess.Popen
            observed = {}
            def spawn(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                wait = process.wait
                first = True
                def controlled_timeout(timeout=None):
                    nonlocal first
                    if first:
                        first = False
                        deadline = time.monotonic() + 3
                        while not ready.exists() and time.monotonic() < deadline:
                            time.sleep(.01)
                        if not ready.exists():
                            process.kill()
                            wait(timeout=3)
                            raise AssertionError('owned child did not start')
                        observed['ready'] = True
                        raise subprocess.TimeoutExpired(args[0], timeout)
                    return wait(timeout=timeout)
                process.wait = controlled_timeout
                return process
            connection = None
            try:
                with patch.object(baseline.subprocess, 'Popen', side_effect=spawn):
                    result = baseline._run_command([sys.executable, '-c', parent_code, child_code, str(ready)], ROOT)
                self.assertEqual(result, (124, True))
                self.assertTrue(observed.get('ready'))
                try:
                    connection = socket.create_connection(('127.0.0.1', int(ready.read_text())), timeout=1)
                    connection.sendall(b'probe')
                    still_alive = connection.recv(64) == b'owned-child-canary'
                except OSError:
                    still_alive = False
                self.assertFalse(still_alive, 'timed-out check left its owned listener alive')
            finally:
                # The old direct-child-only implementation must not leak its reproduction.
                if connection is not None:
                    with contextlib.suppress(OSError):
                        connection.sendall(b'stop')
                    connection.close()

    def test_cleanup_failure_preserves_child_artifacts_and_stops_the_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'baseline'
            child = root / 'package'
            def fail(command, cwd, **kwargs):
                child.mkdir()
                (child / 'synthetic-canary').write_text('keep')
                raise baseline._ProcessCleanupError()
            with patch.object(baseline, '_suite', return_value=[('package_smoke', ['fixed'], child)]), \
                 patch.object(baseline, '_run_command', side_effect=fail) as runner:
                with self.assertRaises(baseline._ProcessCleanupError):
                    baseline.run_baseline(root)
            self.assertEqual(runner.call_count, 1)
            self.assertEqual((child / 'synthetic-canary').read_text(), 'keep')
            self.assertFalse((root / 'production-baseline-evidence.json').exists())

    def test_unavailable_supervision_refuses_before_launch(self):
        with patch.object(baseline, '_process_group_available', return_value=False), \
             patch.object(baseline.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(RuntimeError, 'process supervision unavailable'):
                baseline._run_command(['fixed'], ROOT)
        launch.assert_not_called()

    def test_failed_group_stop_is_fatal_and_reap_is_bounded(self):
        process = Mock(pid=12345, returncode=None)
        process.wait.side_effect = subprocess.TimeoutExpired(['fixed'], .1)
        with patch.object(baseline.subprocess, 'Popen', return_value=process), \
             patch.object(baseline.os, 'killpg', side_effect=PermissionError):
            with self.assertRaisesRegex(baseline._ProcessCleanupError, 'cleanup could not be confirmed'):
                baseline._run_command(['fixed'], ROOT, timeout_seconds=.1)
        self.assertEqual(process.wait.call_count, 1)

    def test_reap_timeout_is_fatal_instead_of_claiming_cleanup(self):
        for failure in (subprocess.TimeoutExpired(['fixed'], .1), KeyboardInterrupt()):
            process = Mock(pid=12345, returncode=None)
            process.wait.side_effect = [subprocess.TimeoutExpired(['fixed'], .1), failure]
            with patch.object(baseline.subprocess, 'Popen', return_value=process), \
                 patch.object(baseline.os, 'killpg') as stop:
                with self.assertRaises(baseline._ProcessCleanupError):
                    baseline._run_command(['fixed'], ROOT, timeout_seconds=.1)
            stop.assert_called_once_with(12345, baseline.signal.SIGKILL)
            self.assertEqual(process.wait.call_count, 2)
            self.assertEqual(process.wait.call_args.kwargs, {'timeout': 5})

    def test_interrupt_stops_only_the_owned_group_before_propagating(self):
        process = Mock(pid=12345, returncode=None)
        process.wait.side_effect = [KeyboardInterrupt, -9]
        with patch.object(baseline.subprocess, 'Popen', return_value=process), \
             patch.object(baseline.os, 'killpg') as stop:
            with self.assertRaises(KeyboardInterrupt):
                baseline._run_command(['fixed'], ROOT)
        stop.assert_called_once_with(12345, baseline.signal.SIGKILL)
        self.assertEqual(process.wait.call_args.kwargs, {'timeout': 5})

    def test_process_start_consumes_budget_and_late_success_cannot_pass(self):
        process = Mock(pid=12345, returncode=0)
        process.wait.return_value = 0
        with patch.object(baseline.time, 'monotonic', side_effect=[0, 0, .25, .8]), \
             patch.object(baseline.subprocess, 'Popen', return_value=process) as launch:
            self.assertEqual(baseline._run_command(['fixed'], ROOT, timeout_seconds=1), (0, False))
        self.assertEqual(process.wait.call_args.kwargs, {'timeout': .75})
        self.assertTrue(launch.call_args.kwargs['start_new_session'])
        self.assertEqual(launch.call_args.kwargs['stdout'], subprocess.DEVNULL)
        self.assertEqual(launch.call_args.kwargs['stderr'], subprocess.DEVNULL)
        with patch.object(baseline.time, 'monotonic', side_effect=[0, 0, .25, 1.01]), \
             patch.object(baseline.subprocess, 'Popen', return_value=process), \
             patch.object(baseline.os, 'killpg') as stop:
            self.assertEqual(baseline._run_command(['fixed'], ROOT, timeout_seconds=1), (124, True))
        stop.assert_not_called()  # Never signal a group through an already reaped PID.

    def test_cleanup_failure_cli_output_is_fixed_and_value_free(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(baseline, 'run_baseline', side_effect=baseline._ProcessCleanupError()), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(baseline.main(['--work-dir', '/synthetic-private-path']), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(errors.getvalue(), 'production baseline process cleanup could not be confirmed\n')
