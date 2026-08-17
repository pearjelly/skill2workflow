from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ControlUiContractTests(TestCase):
    def test_operator_ui_surfaces_complete_bounded_and_truncated_scope(self):
        html = (ROOT / "web" / "control.html").read_text(encoding="utf-8")
        javascript = (ROOT / "web" / "control.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "control.css").read_text(encoding="utf-8")

        self.assertIn('id="snapshot-scope"', html)
        self.assertIn('id="load-live"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("validateSnapshotWindow", javascript)
        self.assertIn("renderSnapshotScope", javascript)
        self.assertIn("Complete offline snapshot", javascript)
        self.assertIn("Bounded snapshot", javascript)
        self.assertIn("collection is truncated", javascript)
        self.assertIn("/api/v1/control-snapshot", javascript)
        self.assertIn("loadLiveSnapshot", javascript)
        self.assertIn(".snapshot-scope.is-bounded", css)
        self.assertIn(".snapshot-scope.is-truncated", css)

    def test_live_snapshot_guide_warns_ui_users_about_window_scope(self):
        guide = (ROOT / "docs" / "live-control-snapshot.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Operator UI", guide)
        self.assertIn("truncated collections", guide)
