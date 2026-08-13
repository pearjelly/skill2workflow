import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class LiveControlSnapshotDocumentationTests(TestCase):
    def test_snapshot_schema_publishes_offline_and_live_window_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "control-snapshot-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/control-snapshot-0.1.0.schema.json",
        )
        self.assertIn("schema_version", schema["required"])
        self.assertNotIn("window", schema["required"])
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-control-snapshot-0.1.0",
        )
        self.assertEqual(
            schema["$defs"]["window"]["properties"]["max_items"]["minimum"],
            1,
        )

    def test_operator_guide_defines_auth_bounds_read_only_and_client_safety(self):
        guide = (ROOT / "docs" / "live-control-snapshot.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "GET /api/v1/control-snapshot",
            "Bearer authentication",
            "100 items",
            "1 MiB",
            "Cache-Control: no-store",
            "does not append persisted audit events",
            "HTTPS or loopback HTTP",
            "redirects",
            "0600",
            "--max-items 100",
            "1` through `1000",
            "rejected for `--service-url`",
            "live_control_snapshot_smoke.py",
        ):
            self.assertIn(phrase, guide)

    def test_public_contracts_record_loop_55_and_fixed_route(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        observability = (ROOT / "docs" / "observability.md").read_text(
            encoding="utf-8"
        )
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        release = (ROOT / "docs" / "release-process.md").read_text(
            encoding="utf-8"
        )
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-134 are complete", readme)
        self.assertIn("docs/live-control-snapshot.md", readme)
        self.assertIn("- Completed delivery loops: 1-134", roadmap)
        self.assertIn(
            "| Loop 55: Authenticated Live Operator Snapshot | Complete |",
            roadmap,
        )
        self.assertIn("GET /api/v1/control-snapshot", service)
        self.assertIn("control_snapshot", observability)
        self.assertIn("authenticated live Operator snapshots", changelog)
        self.assertIn("scripts/live_control_snapshot_smoke.py", release)
        self.assertIn("skill2workflow-control-snapshot-0.1.0", stability)
        self.assertIn("control-snapshot-0.1.0.schema.json", stability)
        self.assertIn("live `window` semantics", stability)
