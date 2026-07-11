from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ProductionRoadmapTests(TestCase):
    def test_roadmap_uses_a_rolling_production_readiness_path(self):
        roadmap = _read("ROADMAP.md")

        headings = [
            "## Product Direction",
            "## Status At A Glance",
            "## Production Readiness Path",
            "## Active Loop",
            "## Rolling Loop Queue",
            "## Capability Baseline",
            "## Delivery History",
            "## Release Direction",
            "## Deferred Work",
            "## Roadmap Rules",
        ]
        positions = [roadmap.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

        self.assertIn("self-hosted, single-tenant workflow runtime for one team", roadmap)
        self.assertIn("- Current maturity: Local Evaluation", roadmap)
        self.assertIn("- Active loop: Loop 39, Scoped Live Lark Task Connector", roadmap)
        self.assertIn("- Next maturity gate: Controlled Live Pilot", roadmap)

        self.assertIn("### Local Evaluation", roadmap)
        self.assertIn("**Status:** Achieved.", roadmap)
        self.assertIn("### Controlled Live Pilot", roadmap)
        self.assertIn("**Target loops:** 39-40.", roadmap)
        self.assertIn("### Self-hosted Beta", roadmap)
        self.assertIn("**Target loops:** 41-43.", roadmap)
        self.assertIn("### Production Baseline", roadmap)
        self.assertIn("**Status:** Directional; no loop numbers assigned.", roadmap)

        self.assertIn(
            "| Loop 40: Controlled Live Connector Pilot | Candidate |",
            roadmap,
        )
        self.assertIn(
            "| Loop 41: Self-hosted Runtime Service Boundary | Candidate |",
            roadmap,
        )
        self.assertIn(
            "| Loop 42: Authenticated Ingress And Production Credentials | Candidate |",
            roadmap,
        )
        self.assertIn(
            "| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Candidate |",
            roadmap,
        )

        self.assertIn(
            "SQLite is the minimum production persistence baseline for Self-hosted Beta. "
            "JSON and JSONL remain supported for examples, local development, and evaluation.",
            roadmap,
        )
        self.assertIn("single-instance and single-tenant", roadmap)
        self.assertIn("must not claim exactly-once execution", roadmap)

    def test_roadmap_rules_keep_loop_selection_and_dsl_migration_explicit(self):
        roadmap = _read("ROADMAP.md")

        self.assertIn("- Select only one active loop.", roadmap)
        self.assertIn(
            "- Preserve Workflow DSL compatibility unless a separately approved contract change "
            "defines migration behavior.",
            roadmap,
        )

    def test_roadmap_preserves_complete_delivery_history(self):
        roadmap = _read("ROADMAP.md")
        history_rows = [
            "| Loop 1: Parser | Complete | Frontmatter, hard gates, checklist normalization, source line mapping |",
            "| Loop 2: Compiler / Validator | Complete | Ordered workflow generation, node and edge validation, terminal-node checks |",
            "| Loop 3: Executor | Complete | Local JSON-backed run state, human gate pause/resume, run list and detail |",
            "| Loop 4: LiteGraph | Complete | Static LiteGraph editor, node inspector, run-state coloring, graph validation |",
            "| Loop 5: Control Plane | Complete | Immutable publish, workflow lifecycle index, published-version runs, audit JSONL, connector placeholders |",
            "| Loop 6: Workflow DSL Contract | Complete | JSON Schema, structured validator output, golden workflow fixture coverage |",
            "| Loop 7: Visual Write-Back | Complete | `write-back` CLI, `Save DSL`, source Workflow DSL embedding, topology-preserving write-back |",
            "| Loop 8: Runtime Durability | Complete | Storage boundary, SQLite run state, SQLite workflow registry, SQLite audit events, JSON import path |",
            "| Loop 9: Control Plane Hardening | Complete | `resume-published`, `control-runs`, `control-run`, audit filters, deprecated-version guard |",
            "| Loop 10: Connector Runtime MVP | Complete | Active connector manifests, manual and HTTP bindings, HTTP execution, connector run events, connector audit events |",
            "| Loop 11: Authoring Experience | Complete | Example gallery, richer LiteGraph parameter forms, safe action/retry/HTTP request write-back, authoring docs |",
            "| Loop 12: Open Source Release Readiness | Complete | `CONTRIBUTING.md`, issue templates, release notes, DSL compatibility policy, stability boundaries |",
            "| Loop 13: Local Control Plane UI | Complete | `control-snapshot`, example snapshot fixture, static control-plane inspector, docs |",
            "| Loop 14: Release Tagging | Complete | Annotated `v0.1.0` tag, GitHub release, release notes published from verified `main` |",
            "| Loop 15: Release Automation | Complete | Read-only release preflight script, version/tag/notes guards, CI dry-run, maintainer docs |",
            "| Loop 16: Workflow Example Pack | Complete | Enterprise example skills, synchronized Workflow DSL and LiteGraph fixtures, example docs and gallery entries |",
            "| Loop 17: Connector Runtime Hardening | Complete | Deterministic HTTP connector tests, timeout/error normalization, retry/timeout docs, credential boundary docs |",
            "| Loop 18: Control Plane Operator UX | Complete | Snapshot operator insights, static Operator view, attention/recent/connector/version tables, docs |",
            "| Loop 19: Demo And Contributor Onboarding | Complete | Resettable local demo helper, generated onboarding artifacts, README/HARNESS entry path, tests |",
            "| Loop 20: Packaging And Installability | Complete | Package metadata guards, editable install smoke helper, installed console-script verification, contributor docs |",
            "| Loop 21: Runtime Policy And Recovery | Complete | Connector retry policy execution, retry/recovery events, audit promotion, runtime policy docs |",
            "| Loop 22: Credential Boundary And Secret Hygiene | Complete | Credential boundary docs, committed-fixture secret hygiene scanner, CI guardrail, contributor guidance |",
            "| Loop 23: Trigger And Local Run API | Complete | Trigger envelope, local trigger command, run-start audit metadata, trigger docs |",
            "| Loop 24: Workflow Inputs And Run Context | Complete | Trigger input persistence, durable run context, compact audit boundary, executor context tests |",
            "| Loop 25: Credential Provider Interface | Complete | Local credential provider, connector handle metadata, credential-file CLI path, leakage tests |",
            "| Loop 26: Local Webhook Adapter | Complete | Local webhook request contract, stdlib webhook server, trigger-boundary adapter, JSON/SQLite tests, docs |",
            "| Loop 27: Run Overlay In Visual Editor | Complete | Read-only run overlay contract, LiteGraph node overlays, control snapshot `node_overlays`, static Nodes view, docs |",
            "| Loop 28: Pilot Playbook And Example | Complete | Local customer-support pilot smoke, webhook-triggered scenario, credential handle proof, snapshot and LiteGraph overlay artifacts, pilot docs |",
            "| Loop 29: Scheduled Trigger Boundary | Complete | Deterministic local schedule contract, schedule CLI, due-run helper, audit tests, schedule smoke, docs |",
            "| Loop 30: Trigger Input Mapping | Complete | Body-only HTTP connector input mapping from durable trigger context, validator/schema coverage, CLI/webhook/schedule tests, docs |",
            "| Loop 31: Connector Extension Contract | Complete | Minimum connector manifest contract, execution handoff boundary, credential/audit rules, registry contract tests, docs |",
            "| Loop 32: Pilot Scenario Pack | Complete | Multi-scenario local pilot pack for customer support, sales renewal, and risk exception workflows, with mapped connector input evidence and artifacts |",
            "| Loop 33: Connector Extension Prototype | Complete | Explicit local external connector fixture, narrow runtime registration, published workflow smoke, credential-handle isolation, and compact audit evidence |",
            "| Loop 34: Connector Packaging Boundary | Complete | Repeatable local connector package layout, explicit-loading smoke contract, compatibility notes, and stability boundaries |",
            "| Loop 35: First Product Connector Candidate | Complete | Lark/Feishu task connector selected, alternatives compared, package boundary and dry-run smoke plan documented |",
            "| Loop 36: First Product Connector Package Smoke | Complete | Lark/Feishu task connector dry-run package fixture, explicit-loading smoke, credential-handle evidence, and compact connector metadata |",
            "| Loop 37: Product Connector Pilot Scenario | Complete | Sales renewal risk workflow using the Lark/Feishu task dry-run connector after a manual gate, with webhook trigger, audit, snapshot, and LiteGraph overlay artifacts |",
            "| Loop 38: Live Connector Readiness Review | Complete | Decision note approving only scoped live Lark/Feishu `create_task` follow-up, with credential, idempotency, failure, audit, test, and rollback boundaries |",
        ]

        for row in history_rows:
            with self.subTest(row=row):
                self.assertIn(row, roadmap)

    def test_loop_39_completion_requires_one_explicitly_enabled_live_task(self):
        roadmap = _read("ROADMAP.md")

        self.assertIn(
            "The project can create one live Lark/Feishu task through an explicitly enabled local connector path.",
            roadmap,
        )

    def test_readme_summarizes_without_copying_the_rolling_queue(self):
        readme = _read("README.md")

        self.assertIn("Current maturity: Local Evaluation", readme)
        self.assertIn("Delivery Loops 1-38 are complete", readme)
        self.assertIn("Loop 39", readme)
        self.assertIn("self-hosted, single-tenant runtime for one team", readme)
        self.assertIn("`ROADMAP.md`", readme)
        candidate_loop_titles = [
            "Loop 40: Controlled Live Connector Pilot",
            "Loop 41: Self-hosted Runtime Service Boundary",
            "Loop 42: Authenticated Ingress And Production Credentials",
            "Loop 43: Durable Recurring Scheduling And Safe Dispatch",
        ]
        for title in candidate_loop_titles:
            with self.subTest(title=title):
                self.assertNotIn(title, readme)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
