import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteBackupInventoryDocumentationTests(TestCase):
    def test_remote_backup_inventory_contract_is_documented_and_schema_bound(self):
        guide = (ROOT / "docs" / "remote-backup-inventory.md").read_text(encoding="utf-8")
        schema = json.loads(
            (ROOT / "schemas" / "remote-backup-inventory-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("GET /api/v1/backup-inventory", guide)
        self.assertIn("service-backup-inventory", guide)
        self.assertIn("runtime.backup_parent_dir", guide)
        self.assertIn("never exports backup names", guide)
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-remote-backup-inventory-0.1.0",
        )
        self.assertEqual(schema["properties"]["backups"]["maxItems"], 100)
        self.assertEqual(
            schema["properties"]["window"]["$ref"], "#/$defs/window"
        )

    def test_service_config_schema_keeps_backup_parent_optional(self):
        schema = json.loads(
            (ROOT / "schemas" / "service-config-0.2.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        runtime = schema["properties"]["runtime"]
        self.assertNotIn("backup_parent_dir", runtime["required"])
        self.assertEqual(runtime["properties"]["backup_parent_dir"]["type"], "string")
