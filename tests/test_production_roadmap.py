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
        self.assertIn("- Current maturity: Self-hosted Beta", roadmap)
        self.assertIn("- Completed delivery loops: 1-171", roadmap)
        self.assertIn("- Active loop: None; Loop 171 is complete with bounded local JSON control index reads", roadmap)
        self.assertIn("- Next maturity gate: Production Baseline", roadmap)
        self.assertIn("docs/controlled-pilot-deferral-review.md", roadmap)
        self.assertIn("This rolling queue is ordered. Loop 171 is complete", roadmap)

        self.assertIn("### Local Evaluation", roadmap)
        self.assertIn("**Status:** Achieved.", roadmap)
        self.assertIn("### Controlled Live Pilot", roadmap)
        self.assertIn("**Target loops:** 40.", roadmap)
        self.assertIn("### Self-hosted Beta", roadmap)
        self.assertIn("**Target loops:** 41-43.", roadmap)
        self.assertIn("**Status:** Achieved.", roadmap)
        self.assertIn("### Production Baseline", roadmap)
        self.assertIn(
            "**Status:** Directional; Loops 44-171 complete, further loop numbers unassigned.",
            roadmap,
        )

        self.assertIn(
            "| Loop 39: Scoped Live Lark Task Connector | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 40: Controlled Live Connector Pilot | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 41: Self-hosted Runtime Service Boundary | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 42: Authenticated Ingress And Production Credentials | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 44: Verified Backup And Restore | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 101: Cross-Database Operator-Action Recovery | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 103: Uniform Metrics Request Boundary | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 104: Startup-Shutdown Race Protection | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 105: Atomic Lifecycle State Transitions | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 106: Atomic Shutdown Admission | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 107: Atomic Scheduler Dispatch Admission | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 108: Live In-Flight Request Pressure Metrics | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 109: Live Scheduler Dispatch Pressure Metrics | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 110: Bounded Service Readiness Waiting | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 111: Prometheus Alert Starter Pack | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 112: Grafana Dashboard Starter Pack | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 113: Release Artifact Provenance Manifest | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 149: Release Artifact SPDX SBOM | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 150: Reproducible Release Artifact Builds | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 151: Bounded Service Soak And Cutover Evidence | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 160: Protected Redacted Remote Backup Inventory | Complete |",
            roadmap,
        )
        self.assertIn("### Loop 160: Protected Redacted Remote Backup Inventory", roadmap)
        self.assertIn(
            "| Loop 165: Bounded One-Shot Schedule Document Reads | Complete |",
            roadmap,
        )
        self.assertIn("### Loop 165: Bounded One-Shot Schedule Document Reads", roadmap)
        self.assertIn(
            "| Loop 114: Bounded Connector Retry Backoff | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 115: Bounded Global Workflow Deadline | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 116: Lease-Owned Workflow Deadline Sweep | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 117: Filtered Cursor-Paged Run Discovery | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 118: Per-Node Active Execution Deadlines | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 119: Bounded Built-in HTTP Connector Payloads | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 120: Atomic First-Use SQLite State Initialization | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 121: Bounded Local Audit Inspection | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 122: Bounded Offline Control Snapshots | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 123: Bounded Local Run Discovery | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 124: Bounded Local Backup Inventory | Complete |",
            roadmap,
        )
        self.assertIn("### Loop 124: Bounded Local Backup Inventory", roadmap)
        self.assertIn(
            "| Loop 125: Bounded Backup Retention Planning | Complete |",
            roadmap,
        )
        self.assertIn("### Loop 125: Bounded Backup Retention Planning", roadmap)
        self.assertIn(
            "| Loop 126: Bounded Local Schedule Inspection | Complete |",
            roadmap,
        )
        self.assertIn("### Loop 126: Bounded Local Schedule Inspection", roadmap)
        self.assertIn(
            "| Loop 45: State Upgrade And Migration | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 91: Bounded Remote Workflow Inventory | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 92: Policy-bound Remote Retention Readiness | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 93: Remote Operational Readiness | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 94: Bounded Request-Body Reads | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 98: Lifecycle Event-Logger Isolation | Complete |",
            roadmap,
        )
        self.assertIn("### Loop 98: Lifecycle Event-Logger Isolation", roadmap)
        self.assertIn(
            "| Loop 99: Deterministic Service Teardown | Complete |",
            roadmap,
        )
        self.assertIn("### Loop 99: Deterministic Service Teardown", roadmap)
        self.assertIn(
            "| Loop 46: Runtime Observability Export | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 47: Data Retention And Disposal | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 64: Declarative Fallback Transitions | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 69: Stable Workflow Version Promotion Aliases | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 70: Published Artifact Integrity Verification | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 71: Reviewable Workflow Releases | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 72: Atomic Workflow Alias Promotion | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 73: Atomic Workflow Registry Mutations | Complete |",
            roadmap,
        )
        self.assertIn(
            "| Loop 74: Workflow Artifact Consistency | Complete |",
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
            "| Loop 39: Scoped Live Lark Task Connector | Complete | Explicit live `create_task` opt-in, fake-transport coverage, native provider idempotency, redaction and rollback boundaries, and one redacted real-validation evidence note |",
            "| Loop 40: Controlled Live Connector Pilot | Complete | Paid assisted five-day, five-run Pilot with two private cases, a human rejection, safety exercises, fixed verification, a `continue` decision, and finalized redacted evidence |",
            "| Loop 41: Self-hosted Runtime Service Boundary | Complete | Versioned service configuration, loopback-only ingress, health/readiness probes, graceful signal shutdown, SQLite restart continuity, operator guide, and real-process smoke evidence |",
            "| Loop 42: Authenticated Ingress And Production Credentials | Complete | File-backed bearer authentication, execution-time directory credentials, compact ingress audit, request-size guard, external TLS contract, and security smoke evidence |",
            "| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete | Persistent interval schedules, explicit missed-run policy, claim-before-execute dispatch ledger, restart recovery, SQLite lease exclusion, standby takeover, and real-process evidence |",
            "| Loop 44: Verified Backup And Restore | Complete | Offline three-database locking, referenced workflow artifacts, owner-only manifest, SHA-256 and integrity verification, atomic new-directory restore, credential exclusion, and real-process recovery drill |",
            "| Loop 45: State Upgrade And Migration | Complete | Owner-only layout marker, read-only legacy/current/future preflight, mandatory pre-upgrade backup, source-preserving atomic copy upgrade, rollback boundary, and real-process cutover drill |",
            "| Loop 46: Runtime Observability Export | Complete | Authenticated Prometheus aggregate metrics, fixed status/route labels, process-local HTTP counters, strict operational NDJSON, and real-process leakage evidence |",
            "| Loop 47: Data Retention And Disposal | Complete | Versioned fixed retention policy, aggregate stopped-state plan, protected waiting/claimed state, secure-delete vacuumed copy, atomic publication, and real-process cutover evidence |",
        ]

        for row in history_rows:
            with self.subTest(row=row):
                self.assertIn(row, roadmap)

    def test_loop_39_completion_requires_one_explicitly_enabled_live_task(self):
        roadmap = _read("ROADMAP.md")

        self.assertIn(
            "docs/lark-live-connector-validation.md",
            roadmap,
        )
        self.assertIn(
            "Live behavior remains limited to the fixed `create_task` action.",
            roadmap,
        )
        self.assertIn(
            "The one scoped live connector validation is not the controlled real-team business-workflow pilot required for Loop 40.",
            roadmap,
        )

    def test_readme_summarizes_without_copying_the_rolling_queue(self):
        readme = _read("README.md")

        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("Delivery Loops 1-171 are complete", readme)
        self.assertIn("Loop 40", readme)
        self.assertIn("self-hosted, single-tenant runtime for one team", readme)
        self.assertIn("`ROADMAP.md`", readme)
        self.assertIn("Loop 40 completed a paid assisted Pilot", readme)
        candidate_loop_titles = [
            "Loop 42: Authenticated Ingress And Production Credentials",
            "Loop 43: Durable Recurring Scheduling And Safe Dispatch",
        ]
        for title in candidate_loop_titles:
            with self.subTest(title=title):
                self.assertNotIn(title, readme)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
