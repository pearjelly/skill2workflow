import contextlib
import http.client
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from unittest import TestCase
from unittest.mock import patch
from tests.http_fixtures import ThreadingHTTPServer

from scripts.release_manifest import PACKAGED_UI_DATA_FILES
from skill2workflow import ui


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = sorted(name.removeprefix('data/share/skill2workflow/')
                for name in PACKAGED_UI_DATA_FILES)
REFUSAL = b'{"error":"UI asset is not available"}'


@contextlib.contextmanager
def server(root):
    ready = threading.Event()
    state = {}
    def callback(value):
        state['server'] = value
        ready.set()
    with patch('skill2workflow.ui.find_ui_root', return_value=root), \
         patch('skill2workflow.ui.ThreadingHTTPServer', ThreadingHTTPServer):
        thread = threading.Thread(target=ui.serve_ui, kwargs={
            'port': 0, 'ready_callback': callback}, daemon=True)
        thread.start()
        if not ready.wait(3):
            raise AssertionError('UI did not start')
        try:
            yield state['server'].server_port
        finally:
            state['server'].shutdown()
            thread.join(3)
            if thread.is_alive():
                raise AssertionError('UI did not close')


def request(port, path, method='GET'):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.putrequest(method, path, skip_host=True)
        connection.putheader('Host', '127.0.0.1')
        connection.endheaders()
        response = connection.getresponse()
        return response.status, dict(response.headers), response.read()
    finally:
        connection.close()


class UiStaticBoundaryTests(TestCase):
    def fixture(self, root):
        for relative in PUBLIC:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def refused(self, port, path, method='GET'):
        status, headers, body = request(port, path, method)
        self.assertEqual(status, 404, path)
        self.assertEqual(headers.get('Cache-Control'), 'no-store')
        self.assertEqual(headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(int(headers['Content-Length']), len(REFUSAL))
        self.assertEqual(body, b'' if method == 'HEAD' else REFUSAL)

    def test_all_packaged_assets_and_head_are_exact_with_safe_editor_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            with server(root) as port:
                for relative in PUBLIC:
                    expected = (root / relative).read_bytes()
                    for method in ('GET', 'HEAD'):
                        status, headers, body = request(port, '/' + relative, method)
                        self.assertEqual(status, 200, relative)
                        self.assertEqual(int(headers['Content-Length']), len(expected))
                        self.assertEqual(headers.get('X-Content-Type-Options'), 'nosniff')
                        self.assertEqual(body, expected if method == 'GET' else b'')
                for path in ('/', '/web'):
                    for method in ('GET', 'HEAD'):
                        status, headers, body = request(port, path, method)
                        self.assertEqual(status, 307)
                        self.assertEqual(headers.get('Location'), '/web/')
                        self.assertEqual(body, b'')
                for path in ('/web/', '/web/index.html?v=1'):
                    self.assertEqual(request(port, path)[2], (root / 'web/index.html').read_bytes())

    def test_private_neighbors_and_directories_are_not_a_file_browser(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            paths = ('README.md', '.git/config', '.impeccable/surfaces/editor.md',
                     'runtime/ingress.token', 'examples/private.json', 'web/private.json')
            for relative in paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('synthetic-private-file-canary', encoding='utf-8')
            with server(root) as port:
                for path in paths + ('examples/', 'web/vendor/', 'web/missing.html'):
                    for method in ('GET', 'HEAD'):
                        self.refused(port, '/' + path, method)

    def test_noncanonical_paths_never_become_filesystem_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            with server(root) as port:
                for path in ('/web/../web/app.js', '/web//app.js', '/%77eb/app.js',
                             '/web/%2e%2e/README.md', '/web%2fapp.js', '/web/app.js/',
                             '/web/app.js#fragment', 'http://example.invalid/web/app.js',
                             'http://[invalid'):
                    for method in ('GET', 'HEAD'):
                        self.refused(port, path, method)

    def test_file_and_directory_symlinks_cannot_expand_the_public_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'public'
            self.fixture(root)
            private = Path(temporary) / 'private'
            private.mkdir()
            (private / 'app.js').write_text('synthetic-private-file-canary', encoding='utf-8')
            (root / 'web/app.js').unlink()
            (root / 'web/app.js').symlink_to(private / 'app.js')
            shutil.rmtree(root / 'web/vendor')
            (root / 'web/vendor').symlink_to(private, target_is_directory=True)
            with server(root) as port:
                for path in ('/web/app.js', '/web/vendor/litegraph-0.7.18/LICENSE'):
                    for method in ('GET', 'HEAD'):
                        self.refused(port, path, method)

    def test_nonregular_or_oversized_public_names_are_refused_without_blocking(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            (root / 'web/app.js').unlink()
            os.mkfifo(root / 'web/app.js')
            with (root / 'web/control.js').open('wb') as stream:
                stream.truncate(8 * 1024 * 1024 + 1)
            with server(root) as port:
                self.refused(port, '/web/app.js')
                self.refused(port, '/web/control.js')

    def test_runtime_inventory_matches_release_gate(self):
        self.assertEqual(set(ui.UI_STATIC_FILES), set(PUBLIC))
        guide = (ROOT / 'docs/installed-ui.md').read_text(encoding='utf-8')
        for phrase in ('Fixed static asset boundary', 'GET and HEAD', '8 MiB',
                       'symlink components', 'unavailable primitives fail closed',
                       'generic `python -m', 'file picker'):
            self.assertIn(phrase, guide)

    def test_leaf_replacement_cannot_redirect_an_admitted_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'public'
            self.fixture(root)
            private = Path(temporary) / 'private.js'
            private.write_text('synthetic-private-file-canary', encoding='utf-8')
            original_open = os.open
            def replace_then_open(path, flags, *args, **kwargs):
                if path == 'app.js':
                    (root / 'web/app.js').unlink()
                    (root / 'web/app.js').symlink_to(private)
                return original_open(path, flags, *args, **kwargs)
            with server(root) as port, patch('skill2workflow.ui.os.open', side_effect=replace_then_open):
                self.refused(port, '/web/app.js')

    def test_parent_replacement_does_not_redirect_an_open_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'public'
            self.fixture(root)
            expected = (root / 'web/app.js').read_bytes()
            private = Path(temporary) / 'private'
            private.mkdir()
            (private / 'app.js').write_text('synthetic-private-file-canary', encoding='utf-8')
            original_open = os.open
            def replace_then_open(path, flags, *args, **kwargs):
                if path == 'app.js':
                    (root / 'web').rename(root / 'pinned-web')
                    (root / 'web').symlink_to(private, target_is_directory=True)
                return original_open(path, flags, *args, **kwargs)
            with server(root) as port, patch('skill2workflow.ui.os.open', side_effect=replace_then_open):
                self.assertEqual(request(port, '/web/app.js')[2], expected)

    def test_unavailable_no_follow_support_fails_closed_before_open(self):
        with tempfile.TemporaryDirectory() as temporary:
            with server(Path(temporary)) as port, patch('skill2workflow.ui.os.O_NOFOLLOW', 0), \
                 patch('skill2workflow.ui.os.open') as opened:
                self.refused(port, '/web/app.js')
                opened.assert_not_called()

    def test_installed_qualification_requires_complete_refusal_evidence(self):
        from scripts import package_smoke
        complete = {'ok': True, 'installed': True, 'cases_verified': 10, 'private_file_excluded': True}
        for value in (complete, {}, dict(complete, cases_verified=9), dict(complete, private_file_excluded=False)):
            with patch('scripts.package_smoke._run', return_value=json.dumps(value)):
                if value == complete:
                    self.assertTrue(package_smoke._qualify_installed_ui_static(Path('/repo'), Path('/venv/bin/cli'), Path('/isolated')))
                else:
                    with self.assertRaisesRegex(RuntimeError, 'qualification failed'):
                        package_smoke._qualify_installed_ui_static(Path('/repo'), Path('/venv/bin/cli'), Path('/isolated'))

    def test_head_never_invokes_live_proxy_or_local_authoring_helpers(self):
        with tempfile.TemporaryDirectory() as temporary:
            with server(Path(temporary)) as port, \
                 patch('skill2workflow.ui.fetch_live_control_snapshot') as fetch, \
                 patch('skill2workflow.ui.build_workflow_preflight') as preflight:
                for path in ('/api/v1/control-snapshot', '/api/v1/draft-input-preflights'):
                    self.refused(port, path, 'HEAD')
                fetch.assert_not_called()
                preflight.assert_not_called()
