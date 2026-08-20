from pathlib import Path
import json
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class SecurityBoundaryDocumentationTests(TestCase):
    def test_service_config_schema_matches_runtime_security_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "service-config-0.2.0.schema.json").read_text(encoding="utf-8")
        )

        self.assertEqual(schema["properties"]["schema_version"]["const"], "skill2workflow-service-0.2.0")
        self.assertEqual(schema["properties"]["runtime"]["properties"]["storage"]["const"], "sqlite")
        self.assertEqual(
            schema["properties"]["auth"]["properties"]["provider"]["const"],
            "bearer_token_file",
        )
        self.assertEqual(
            schema["properties"]["credentials"]["properties"]["provider"]["const"],
            "directory",
        )
        self.assertFalse(schema["additionalProperties"])

    def test_security_guide_documents_fail_closed_auth_credentials_and_tls_boundary(self):
        guide = (ROOT / "docs" / "security-boundary.md").read_text(encoding="utf-8")

        self.assertIn("skill2workflow-service-0.2.0", guide)
        self.assertIn("bearer_token_file", guide)
        self.assertIn("chmod 600", guide)
        self.assertIn("HTTP 401", guide)
        self.assertIn("reread", guide)
        self.assertIn("service-token-rotate", guide)
        self.assertIn("service-token-rotation.md", guide)
        self.assertIn("provider: `directory`", guide)
        self.assertIn("execution time", guide)
        self.assertIn("1 MiB", guide)
        self.assertIn("external TLS termination", guide)
        self.assertIn("loopback", guide)
        self.assertIn("must not contain secret values", guide)
        self.assertIn("security_boundary_smoke.py", guide)
        self.assertIn("service unavailable", guide)
        self.assertIn("unsafe_credential_file_blocked", guide)
        self.assertIn("not multi-tenant RBAC", guide)

        credential_guide = (ROOT / "docs" / "credential-boundary.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("64 KiB", credential_guide)
        self.assertIn("regular-file descriptor", credential_guide)
        self.assertIn("mode `0600`", credential_guide)
        self.assertIn("symbolic links", credential_guide)

    def test_readme_and_roadmap_preserve_loop_42_with_completed_beta_gate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-222 are complete", readme)
        self.assertIn("docs/security-boundary.md", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("| Loop 42: Authenticated Ingress And Production Credentials | Complete |", roadmap)
        self.assertIn("| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete |", roadmap)
        self.assertIn("| Loop 54: Descriptor-bound Connector Credentials | Complete |", roadmap)
