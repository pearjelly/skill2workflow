import threading
import urllib.request
from pathlib import Path
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.ui import find_ui_root, serve_ui


ROOT = Path(__file__).resolve().parents[1]


class UiTests(TestCase):
    def test_find_ui_root_discovers_source_assets(self):
        root = find_ui_root()

        self.assertEqual(root, ROOT)
        self.assertTrue((root / "web" / "index.html").is_file())
        self.assertTrue((root / "examples" / "control-plane-snapshot.json").is_file())

    def test_ui_server_is_loopback_only_and_serves_static_assets_once(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            serve_ui(host="0.0.0.0", port=0, once=True)

        observed = {}

        def ready(server):
            observed["port"] = server.server_port

        thread = threading.Thread(
            target=serve_ui,
            kwargs={"host": "127.0.0.1", "port": 0, "once": True, "ready_callback": ready},
            daemon=True,
        )
        thread.start()
        for _ in range(100):
            if "port" in observed:
                break
            thread.join(0.01)
        self.assertIn("port", observed)
        with urllib.request.urlopen(
            f"http://127.0.0.1:{observed['port']}/web/index.html", timeout=2
        ) as response:
            body = response.read()
            self.assertEqual(response.status, 200)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertIn(b"Workflow DSL Visual Editor", body)

    def test_cli_ui_command_forwards_loopback_server_options(self):
        captured = {}

        def fake_serve_ui(**kwargs):
            captured.update(kwargs)

        from unittest.mock import patch

        with patch("skill2workflow.cli.serve_ui", side_effect=fake_serve_ui):
            exit_code = main(["ui", "--host", "localhost", "--port", "4317", "--once"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            captured,
            {"host": "localhost", "port": 4317, "once": True},
        )
