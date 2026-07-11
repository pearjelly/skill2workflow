# Live Connector Readiness Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Loop 38 by documenting and testing the readiness decision for scoped live Lark/Feishu task creation.

**Architecture:** This loop is intentionally documentation-first. A docs contract test locks the decision note, connector safety boundary, and Roadmap transition before any live connector implementation starts.

**Tech Stack:** Python 3.9 standard library, `unittest`, Markdown documentation.

## Global Constraints

- Workflow DSL remains the execution truth source.
- `examples/connectors/lark_task_connector.py` must remain dry-run-only in Loop 38.
- Do not add live Lark/Feishu API calls, OAuth, token refresh, hosted callbacks, automatic connector discovery, queues, production schedulers, marketplace behavior, or broad SaaS connector catalogs.
- Credential material must stay outside Workflow DSL, trigger input, run state, and audit events.
- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.

---

### Task 1: Readiness Decision Contract

**Files:**
- Create: `tests/test_live_connector_readiness.py`
- Create: `docs/lark-live-connector-readiness.md`
- Modify: `docs/connectors.md`

**Interfaces:**
- Consumes: current Loop 36 and Loop 37 dry-run evidence in `docs/connectors.md` and `ROADMAP.md`
- Produces: a tested readiness decision that later Loop 39 work can implement without changing the decision criteria

- [x] **Step 1: Write the failing test**

Create `tests/test_live_connector_readiness.py` with assertions for:

- decision title and explicit proceed/defer outcome
- approved `create_task` action surface
- credential handle and no-secret surfaces
- idempotency and duplicate prevention
- failure-mode handling
- compact audit redaction
- fake-transport local test strategy
- rollback and feature flag boundaries
- Loop 38 complete / Loop 39 next Roadmap state

- [x] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_live_connector_readiness -v`

Expected: fail because `docs/lark-live-connector-readiness.md` does not exist.

- [x] **Step 3: Write minimal documentation**

Create `docs/lark-live-connector-readiness.md` with the tested sections and add a short reference from `docs/connectors.md`.

- [x] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests.test_live_connector_readiness -v`

Expected: pass.

### Task 2: Roadmap Transition

**Files:**
- Modify: `ROADMAP.md`
- Modify: `tests/test_product_connector_pilot_roadmap.py`
- Modify: `tests/test_first_product_connector_candidate_docs.py`

**Interfaces:**
- Consumes: `docs/lark-live-connector-readiness.md`
- Produces: Roadmap state where Loop 38 is complete and Loop 39 is the scoped live implementation loop

- [x] **Step 1: Update roadmap tests**

Change roadmap assertions from Loop 38 next to Loop 38 complete and Loop 39 next, while preserving the dry-run-only safety boundary for Loop 38.

- [x] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m unittest tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs -v`

Expected: fail until `ROADMAP.md` is updated.

- [x] **Step 3: Update `ROADMAP.md`**

Move Loop 38 into Completed Loops, set Loop 39 as the active loop, and describe Loop 39 as a scoped live `create_task` implementation guarded by the Loop 38 decision.

- [x] **Step 4: Run focused roadmap tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_live_connector_readiness tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs -v`

Expected: pass.

### Task 3: Verification And PR

**Files:**
- Modify: `docs/superpowers/plans/2026-07-10-live-connector-readiness-review.md`

**Interfaces:**
- Consumes: all files changed in Tasks 1 and 2
- Produces: verified Loop 38 branch and draft PR

- [x] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all commands pass.

- [x] **Step 2: Mark this plan complete**

Update checkboxes in this file for completed steps.

- [x] **Step 3: Commit and open PR**

Run:

```bash
git add ROADMAP.md docs/connectors.md docs/lark-live-connector-readiness.md docs/superpowers/plans/2026-07-10-live-connector-readiness-review.md tests/test_live_connector_readiness.py tests/test_product_connector_pilot_roadmap.py tests/test_first_product_connector_candidate_docs.py
git commit -m "docs: add live connector readiness review"
git push -u origin loop-38-live-connector-readiness
gh pr create --draft --base main --head loop-38-live-connector-readiness --title "Loop 38: live connector readiness review"
```

Expected: draft PR opens against `main`.
