# Connector Packaging Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Loop 33 explicit external connector prototype into a documented, repeatable local connector package boundary.

**Architecture:** Keep the runtime unchanged unless the current explicit loader cannot support the package convention. Use docs as the contract source for package layout, compatibility, stability, and smoke expectations, then add a narrow documentation-contract test so the boundary does not regress.

**Tech Stack:** Python 3.9 standard library, `unittest`, Markdown documentation, existing explicit external connector loader.

## Global Constraints

- Workflow DSL remains the execution truth source.
- Do not add product-specific SaaS connectors.
- Do not add automatic connector discovery, package installation, marketplace indexing, OAuth, hosted callbacks, queues, or production schedulers.
- Do not broaden trigger input mapping beyond the current body-only contract.
- Keep explicit loading and registration as the only supported external connector path.
- Keep runtime dependency-free and standard-library only.

---

### Task 1: Documentation Contract Test

**Files:**
- Create: `tests/test_connector_package_docs.py`

**Interfaces:**
- Consumes: `docs/connectors.md`, `docs/examples.md`, `docs/workflow-dsl-compatibility.md`, `docs/stability.md`
- Produces: focused test coverage for Loop 34 documentation boundaries

- [x] **Step 1: Write the failing docs contract test**

Add tests that assert the docs define:

- connector package layout
- explicit package loading contract
- smoke command contract
- Workflow DSL compatibility separation
- stability separation between explicit fixture loading and automatic discovery

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connector_package_docs -v
```

Expected: failure because the Loop 34 sections are not yet present.

### Task 2: Connector Package Boundary Docs

**Files:**
- Modify: `docs/connectors.md`
- Modify: `docs/examples.md`
- Modify: `docs/workflow-dsl-compatibility.md`
- Modify: `docs/stability.md`

**Interfaces:**
- Consumes: `examples/connectors/local_echo_connector.py`, `load_external_connector(path)`, and `ConnectorRuntime([external_connector])`
- Produces: repeatable local connector package conventions and compatibility/stability notes

- [x] **Step 1: Document connector package layout**

Add a `Connector Package Layout` section to `docs/connectors.md` with:

- reference layout
- required `MANIFEST` and `execute(binding, credential_provider=None, context=None)`
- explicit loader path
- result/audit/credential rules
- out-of-scope list

- [x] **Step 2: Document example package shape**

Update `docs/examples.md` to explain that `examples/connectors/local_echo_connector.py` is the package-shape reference fixture and is verified through the smoke command.

- [x] **Step 3: Document compatibility boundary**

Update `docs/workflow-dsl-compatibility.md` so connector package conventions are separate from Workflow DSL `0.1.0`, while `connector.id` / `connector.kind` remain the DSL binding points.

- [x] **Step 4: Document stability boundary**

Update `docs/stability.md` so minimum manifest fields and explicit local fixture loading for examples are stable enough to copy, while automatic discovery and product connectors remain experimental.

- [x] **Step 5: Verify green**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connector_package_docs -v
```

Expected: tests pass.

### Task 3: Roadmap Completion And Full Verification

**Files:**
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: Loop 34 docs and tests
- Produces: Loop 34 completion state and Loop 35 decision entry

- [x] **Step 1: Update Roadmap**

Move Loop 34 to complete and set Loop 35 as the next decision loop. Keep product-specific connector work gated by package boundary, credential handling, audit behavior, and smoke evidence.

- [x] **Step 2: Run focused verification**

```bash
PYTHONPATH=src python3 -m unittest tests.test_connector_package_docs tests.test_external_connector_smoke -v
python3 scripts/external_connector_smoke.py --work-dir /tmp/skill2workflow-external-connector-loop34
```

- [x] **Step 3: Run full verification**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

- [x] **Step 4: Commit and open draft PR**

```bash
git add ROADMAP.md docs/connectors.md docs/examples.md docs/stability.md docs/workflow-dsl-compatibility.md docs/superpowers/plans/2026-07-07-connector-packaging-boundary.md tests/test_connector_package_docs.py
git commit -m "docs: define connector packaging boundary"
git push -u origin loop-34-connector-packaging-boundary
```
