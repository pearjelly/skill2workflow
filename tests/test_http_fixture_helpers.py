import http.client
import http.server
import inspect
from pathlib import Path
import threading
from unittest import TestCase
from unittest.mock import patch

from tests import http_fixtures


ROOT = Path(__file__).resolve().parents[1]


class HttpFixtureHelperTests(TestCase):
    def test_short_default_and_explicit_intervals_are_forwarded_without_global_patch(self):
        for server_class in (http_fixtures.HTTPServer, http_fixtures.ThreadingHTTPServer):
            with self.subTest(server_class=server_class.__name__):
                with server_class(('127.0.0.1', 0), http.server.BaseHTTPRequestHandler) as server, \
                     patch('http.server.HTTPServer.serve_forever') as run:
                    server.serve_forever()
                    run.assert_called_once_with(poll_interval=0.01)
                    run.reset_mock()
                    server.serve_forever(poll_interval=0.125)
                    run.assert_called_once_with(poll_interval=0.125)
        self.assertEqual(inspect.signature(http.server.HTTPServer.serve_forever)
                         .parameters['poll_interval'].default, 0.5)
        from skill2workflow import ui
        self.assertIs(ui.ThreadingHTTPServer, http.server.ThreadingHTTPServer)

    def test_real_protocol_request_and_clean_joined_shutdown_are_preserved(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', '7')
                self.end_headers()
                self.wfile.write(b'fixture')
        for server_class in (http_fixtures.HTTPServer, http_fixtures.ThreadingHTTPServer):
            with server_class(('127.0.0.1', 0), Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                try:
                    connection.request('GET', '/fixture')
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b'fixture')
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join(3)
                self.assertFalse(thread.is_alive())

    def test_owned_http_fixtures_share_the_test_only_helper(self):
        import tests
        self.assertEqual(Path(tests.__file__).resolve().parent, ROOT / 'tests')
        for name in ('test_cli', 'test_connectors', 'test_control_plane', 'test_executor',
                     'test_live_snapshot', 'test_schedules', 'test_service', 'test_service_client',
                     'test_ui', 'test_webhooks', 'test_workflow_explanation_remote'):
            source = (ROOT / 'tests' / (name + '.py')).read_text(encoding='utf-8')
            self.assertIn('from tests.http_fixtures import HTTPServer', source)
            self.assertNotIn('from http.server import BaseHTTPRequestHandler, HTTPServer', source)
        static = (ROOT / 'tests/test_ui_static_boundary.py').read_text(encoding='utf-8')
        self.assertIn("patch('skill2workflow.ui.ThreadingHTTPServer', ThreadingHTTPServer)", static)
