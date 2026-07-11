# First Product Connector Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Select and document the first product-specific connector candidate without adding connector runtime code.

**Architecture:** Loop 35 is a decision loop. It adds a contract-backed decision note, keeps product connector code out of core, and updates the roadmap so Loop 36 can implement only after the boundary is explicit.

**Tech Stack:** Python 3.9 standard library tests, Markdown docs, existing Workflow DSL and connector package conventions.

## Global Constraints

- Workflow DSL remains the execution source of truth.
- Product connector code must remain outside the built-in connector registry.
- Credential values must remain outside Workflow DSL, connector result summaries, audit events, and committed fixtures.
- Loop 35 must not add automatic discovery, installer, marketplace, OAuth, hosted callbacks, queues, or production schedulers.
- Runtime code changes are out of scope for this loop.

---

### Task 1: Candidate Decision Docs Contract

**Files:**
- Create: `tests/test_first_product_connector_candidate_docs.py`
- Create: `docs/first-product-connector-candidate.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: Loop 34 package contract in `docs/connectors.md`
- Produces: `docs/first-product-connector-candidate.md` as the Loop 36 entry artifact

- [x] **Step 1: Write the failing docs contract test**

Add a unittest that requires the Loop 35 decision note, selected candidate, alternatives, package layout, credential boundary, smoke command, compact audit metadata, and roadmap completion state.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_first_product_connector_candidate_docs -v
```

Expected: fail because `docs/first-product-connector-candidate.md` does not exist yet.

- [x] **Step 2: Add the candidate decision note**

Create `docs/first-product-connector-candidate.md` selecting the Lark/Feishu task connector, defining the first action surface as `create_task`, and documenting package layout, manifest scope, credential handles, smoke strategy, compact audit metadata, and Loop 36 entry conditions.

- [x] **Step 3: Update Roadmap state**

Move Loop 35 to complete, set Loop 36 as next, and keep Loop 37 as a candidate. Update current priority and pilot-readiness text to point at the selected Lark/Feishu task package smoke.

- [x] **Step 4: Verify focused contract**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_first_product_connector_candidate_docs -v
```

Expected: pass.

### Task 2: Full Verification And PR

**Files:**
- Modify: `docs/superpowers/plans/2026-07-08-first-product-connector-candidate.md`

**Interfaces:**
- Consumes: Task 1 docs and roadmap changes
- Produces: draft PR for Loop 35

- [x] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and open draft PR**

Run:

```bash
git add ROADMAP.md docs/first-product-connector-candidate.md docs/superpowers/plans/2026-07-08-first-product-connector-candidate.md tests/test_first_product_connector_candidate_docs.py
git commit -m "docs: select first product connector candidate"
git push -u origin loop-35-first-product-connector-candidate
```
