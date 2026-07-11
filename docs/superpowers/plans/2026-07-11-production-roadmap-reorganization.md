# Production Roadmap Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `ROADMAP.md` around a rolling production-readiness path and align the compact `README.md` summary without changing runtime behavior.

**Architecture:** Keep `ROADMAP.md` as the single source for roadmap state, with one detailed active loop, four candidate loops, maturity gates, a compact capability baseline, and compressed history. Lock the new structure with documentation contract tests, while preserving the existing Loop 35-39 assertions and the user's current uncommitted Roadmap and README work as the editing baseline.

**Tech Stack:** Python 3.9 standard library, `unittest`, Markdown documentation, Git.

## Global Constraints

- Workflow DSL remains the execution source of truth.
- The production direction is self-hosted, single-tenant, and intended for one team.
- Only Loop 39 is active; Loops 40-43 remain candidates until evidence promotes them.
- SQLite is the minimum production persistence baseline; JSON and JSONL remain available for examples, local development, and evaluation.
- Do not claim exactly-once execution; duplicate suppression depends on persisted dispatch state and workflow or connector idempotency.
- Do not implement runtime, connector, storage, scheduling, authentication, or CLI behavior in this change.
- Preserve the approved Loop 39 scope and all existing Loop 35-39 roadmap contract assertions.
- Keep Python runtime dependencies limited to the standard library.
- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.

---

## File Map

- `ROADMAP.md`: authoritative roadmap state, maturity path, active loop, candidate queue, capability baseline, history, release direction, deferred work, and maintenance rules.
- `README.md`: compact maturity and active-priority summary with a pointer to `ROADMAP.md`.
- `tests/test_production_roadmap.py`: documentation contract for roadmap ordering, production boundaries, candidate loops, and README consistency.
- `docs/superpowers/plans/2026-07-11-production-roadmap-reorganization.md`: execution checklist and verification record for this documentation loop.

### Task 1: Production Roadmap Contract And Reorganization

**Files:**
- Create: `tests/test_production_roadmap.py`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-07-11-production-roadmap-design.md`, `docs/lark-live-connector-readiness.md`, and the current uncommitted `ROADMAP.md` reorganization draft
- Produces: one authoritative roadmap organized by production maturity with Loop 39 active and Loops 40-43 candidate

- [x] **Step 1: Write the failing Roadmap contract test**

Create `tests/test_production_roadmap.py` with this initial content:

```python
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

        self.assertIn("SQLite is the minimum production persistence baseline", roadmap)
        self.assertIn("single-instance and single-tenant", roadmap)
        self.assertIn("must not claim exactly-once execution", roadmap)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
```

- [x] **Step 2: Run the Roadmap contract test and confirm the expected failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_production_roadmap -v
```

Expected: FAIL because `ROADMAP.md` does not yet contain `## Product Direction`, the four maturity gates, or candidate Loops 41-43.

- [x] **Step 3: Reorganize `ROADMAP.md` to satisfy the contract**

Use the current uncommitted Roadmap draft as the baseline. Preserve its Loop 39 scope and delivery-history table, then arrange the document under these exact top-level headings and in this exact order:

```markdown
## Product Direction
## Status At A Glance
## Production Readiness Path
## Active Loop
## Rolling Loop Queue
## Capability Baseline
## Delivery History
## Release Direction
## Deferred Work
## Roadmap Rules
```

Under `Product Direction`, state exactly that the near-term target is a `self-hosted, single-tenant workflow runtime for one team`, that the project remains local-first, and that Workflow DSL remains authoritative.

Under `Status At A Glance`, retain the release, schema compatibility, and completed-loop facts and add these exact status lines:

```markdown
- Current maturity: Local Evaluation
- Active loop: Loop 39, Scoped Live Lark Task Connector
- Next maturity gate: Controlled Live Pilot
```

Under `Production Readiness Path`, define these exact gates:

```markdown
### Local Evaluation

**Status:** Achieved.

### Controlled Live Pilot

**Target loops:** 39-40.

### Self-hosted Beta

**Target loops:** 41-43.

### Production Baseline

**Status:** Directional; no loop numbers assigned.
```

Explain that SQLite is the minimum production persistence baseline for Self-hosted Beta, while JSON and JSONL remain supported for examples, local development, and evaluation.

Rename the current `Active Roadmap` heading to `Active Loop`. Keep the existing Loop 39 goal, why-now evidence, decision boundary, approved scope, implementation order, acceptance criteria, required verification, and explicit exclusions. Preserve all existing strings asserted by:

```bash
PYTHONPATH=src python3 -m unittest tests.test_live_connector_readiness tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs -v
```

Replace `Near-Term Loop Queue` with `Rolling Loop Queue` and include these exact table-row prefixes:

```markdown
| Loop 39: Scoped Live Lark Task Connector | Next |
| Loop 40: Controlled Live Connector Pilot | Candidate |
| Loop 41: Self-hosted Runtime Service Boundary | Candidate |
| Loop 42: Authenticated Ingress And Production Credentials | Candidate |
| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Candidate |
```

The queue descriptions must cover, respectively:

- controlled live-pilot runbook, redacted evidence, failure and rollback exercises, and a continue/harden/defer decision;
- one long-running service entry point, validated configuration, health/readiness checks, graceful shutdown, and restart continuity;
- authentication required by default for the production service path, credential-handle resolution, compact security audit evidence, and external TLS termination;
- persistent recurring schedules, restart recovery, missed-run policy, durable dispatch records, and lease or locking semantics for one SQLite-backed service instance.

State that the scope remains `single-instance and single-tenant` and that the roadmap `must not claim exactly-once execution`.

Move the existing five-layer capability table under `Capability Baseline`. Remove the repeated `Pilot Readiness` prose because the new maturity gates replace it. Preserve the complete Loop 1-38 delivery-history table. Keep release direction compact and remove speculative version-by-version capability inventories. Preserve deferred boundaries for multi-tenancy, distributed scheduling, OAuth, hosted secrets, marketplace behavior, broader live SaaS actions, and arbitrary SOP conversion.

- [x] **Step 4: Run the Roadmap and legacy documentation contract tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_production_roadmap tests.test_live_connector_readiness tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs -v
```

Expected: all tests PASS.

- [x] **Step 5: Commit the Roadmap contract and reorganization**

Run:

```bash
git add ROADMAP.md tests/test_production_roadmap.py
git commit -m "docs: organize production roadmap"
```

Expected: one commit containing only the authoritative Roadmap and its focused contract test.

### Task 2: Compact README Roadmap Summary

**Files:**
- Modify: `tests/test_production_roadmap.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the maturity and active-loop language established in Task 1
- Produces: a compact README summary consistent with `ROADMAP.md` but without duplicating the candidate queue

- [x] **Step 1: Add the failing README consistency test**

Add this method to `ProductionRoadmapTests` before `_read`:

```python
    def test_readme_summarizes_without_copying_the_rolling_queue(self):
        readme = _read("README.md")

        self.assertIn("Current maturity: Local Evaluation", readme)
        self.assertIn("Delivery Loops 1-38 are complete", readme)
        self.assertIn("Loop 39", readme)
        self.assertIn("self-hosted, single-tenant runtime for one team", readme)
        self.assertIn("`ROADMAP.md`", readme)
        self.assertNotIn("Loop 40: Controlled Live Connector Pilot", readme)
        self.assertNotIn("Loop 43: Durable Recurring Scheduling And Safe Dispatch", readme)
```

- [x] **Step 2: Run the README test and confirm the expected failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_production_roadmap.ProductionRoadmapTests.test_readme_summarizes_without_copying_the_rolling_queue -v
```

Expected: FAIL because the current README does not state the maturity or self-hosted single-tenant target.

- [x] **Step 3: Replace the README Roadmap summary with the compact approved copy**

Keep the `## Roadmap` heading and `See:` link list. Replace only the prose between them with:

```markdown
Current maturity: Local Evaluation. The local-first harness covers all five approved architecture layers, and Delivery Loops 1-38 are complete.

The active priority is Loop 39: implement only the readiness-approved Lark/Feishu `create_task` live action behind explicit opt-in while keeping dry-run behavior as the default.

The production direction is a self-hosted, single-tenant runtime for one team. See `ROADMAP.md` for the production-readiness gates, rolling Loop queue, acceptance evidence, and deferred boundaries.
```

- [x] **Step 4: Run the README and Roadmap contract tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_production_roadmap -v
```

Expected: both tests PASS.

- [x] **Step 5: Commit the README alignment**

Run:

```bash
git add README.md tests/test_production_roadmap.py
git commit -m "docs: align readme with production roadmap"
```

Expected: one commit containing the README summary and its consistency assertion.

### Task 3: Full Verification And Plan Completion

**Files:**
- Modify: `docs/superpowers/plans/2026-07-11-production-roadmap-reorganization.md`

**Interfaces:**
- Consumes: the Roadmap, README, and tests completed in Tasks 1 and 2
- Produces: a verified documentation change with a completed execution record

- [x] **Step 1: Run the full repository verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: the complete test suite passes, Python compilation exits successfully, secret hygiene reports no findings, and `git diff --check` emits no errors.

- [x] **Step 2: Inspect the final documentation diff and repository state**

Run:

```bash
git diff 282b551..HEAD -- ROADMAP.md README.md tests/test_production_roadmap.py
git status --short
```

Expected: the diff contains only the approved Roadmap reorganization, compact README summary, and documentation contract tests; no unrelated files are modified.

- [x] **Step 3: Mark the execution checklist complete**

Change every completed `- [ ]` checkbox in this plan to `- [x]` after its command has produced the expected result.

- [x] **Step 4: Commit the completed execution record**

Run:

```bash
git add docs/superpowers/plans/2026-07-11-production-roadmap-reorganization.md
git commit -m "docs: complete production roadmap plan"
```

Expected: the final commit contains only the checked execution plan.
