# Connector Extension Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove one explicitly loaded local external connector can run through the existing workflow runtime without becoming a built-in connector.

**Architecture:** Add a narrow `ConnectorRuntime` wrapper that keeps built-in connectors unchanged by default and accepts explicitly registered external connector fixtures. Add one file-based explicit loader for local fixtures, one example `local_echo` connector, and a smoke helper that runs a published workflow through the external connector while preserving credential and audit redaction. Full-suite verification also requires closing short-lived SQLite operation connections to prevent descriptor exhaustion.

**Tech Stack:** Python 3.9 standard library, `unittest`, local JSON/SQLite control-plane state.

## Global Constraints

- Workflow DSL remains the execution truth source.
- Keep the runtime dependency-free and standard-library only.
- Do not add product-specific SaaS connectors.
- Do not add connector marketplace, installer, automatic discovery, OAuth, hosted callbacks, queues, or production schedulers.
- Credential values must not appear in Workflow DSL, run state, smoke result JSON, artifacts, or audit events.
- The default built-in connector registry must stay stable unless a test or smoke explicitly loads the external fixture.

---

### Task 1: External Connector Runtime Contract

**Files:**
- Modify: `src/skill2workflow/connectors.py`
- Modify: `tests/test_connectors.py`
- Create: `examples/connectors/local_echo_connector.py`

**Interfaces:**
- Consumes: existing `validate_connector_manifest(manifest)` and `execute_connector(node, credential_provider=None, context=None)`
- Produces: `ExternalConnector`, `ConnectorRuntime`, and `ConnectorRuntime.execute_connector(node, credential_provider=None, context=None)`

- [x] **Step 1: Write failing tests**

Add tests that import `ConnectorRuntime`, `ExternalConnector`, and `examples/connectors/local_echo_connector.py`, then assert:

- default runtime connector ids remain `["manual", "http"]`
- external fixture manifest validates
- explicit runtime registration adds only `local_echo`
- external connector execution returns a normalized completed result
- missing external connector credentials fail before completion

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors -v
```

Expected: import failure for `ConnectorRuntime` or missing fixture.

- [x] **Step 3: Implement minimal runtime and fixture**

Implement:

- `ExternalConnector(manifest, executor)` dataclass
- `ConnectorRuntime(external_connectors=None)`
- `ConnectorRuntime.list_connectors()`
- `ConnectorRuntime.execute_connector(...)`
- `examples/connectors/local_echo_connector.py` with `MANIFEST` and `execute(binding, credential_provider=None, context=None)`

The fixture should return compact output keys only, plus `credentials: {"status": "resolved", "handles": [...]}` and `input_mapping` summary.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors -v
```

Expected: tests pass.

### Task 2: Control Plane Audit Path

**Files:**
- Modify: `src/skill2workflow/executor.py`
- Modify: `src/skill2workflow/control_plane.py`
- Modify: `tests/test_control_plane.py`

**Interfaces:**
- Consumes: `ConnectorRuntime`
- Produces: `LocalExecutor(..., connector_runtime=None)`, `LocalControlPlane(..., connector_runtime=None)`, and promoted compact credential audit metadata

- [x] **Step 1: Write failing control-plane test**

Add a test that runs a published workflow with `local_echo`, trigger input, and a credential handle. Assert:

- run completes
- run state and audit events do not contain the resolved secret
- connector audit event contains `credential_handles`
- connector audit event contains `input_mapping_status` and `input_mapping_keys`

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_plane.ControlPlaneTests.test_external_connector_runtime_promotes_compact_audit_metadata -v
```

Expected: constructor or execution failure before runtime support is wired.

- [x] **Step 3: Wire runtime through executor and control plane**

Pass `connector_runtime` from `LocalControlPlane` to `LocalExecutor`, call `self.connector_runtime.execute_connector(...)`, copy compact `credentials` summary into node results, and promote `credential_status` / `credential_handles` into audit events.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_plane -v
```

Expected: tests pass.

### Task 3: Explicit Loader And Smoke Command

**Files:**
- Create: `src/skill2workflow/external_connectors.py`
- Create: `src/skill2workflow/external_connector_smoke.py`
- Create: `scripts/external_connector_smoke.py`
- Create: `tests/test_external_connector_smoke.py`

**Interfaces:**
- Consumes: `ConnectorRuntime`, `ExternalConnector`, and `examples/connectors/local_echo_connector.py`
- Produces: `load_external_connector(path: Path) -> ExternalConnector` and `run_external_connector_smoke(repo_root, work_dir, reset=True)`

- [x] **Step 1: Write failing smoke test**

Add a test that calls `run_external_connector_smoke(...)` and asserts:

- result `ok` is true
- `connector_ids` includes `local_echo`
- `default_connector_ids` remains `["manual", "http"]`
- run status is `completed`
- artifacts exist
- result JSON does not include `local-secret-value`

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_external_connector_smoke -v
```

Expected: missing module/function failure.

- [x] **Step 3: Implement loader, smoke helper, and script**

The smoke helper should explicitly load `examples/connectors/local_echo_connector.py`, publish a local workflow, trigger it with non-secret input, export workflow/run/audit/snapshot artifacts, and return compact summaries only.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_external_connector_smoke -v
python3 scripts/external_connector_smoke.py --work-dir /tmp/skill2workflow-external-connector-loop33
```

Expected: both pass and the script prints `ok: true`.

### Task 4: Documentation And Roadmap

**Files:**
- Modify: `README.md`
- Modify: `docs/connectors.md`
- Modify: `docs/examples.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: external connector smoke command and runtime contract
- Produces: evaluator-facing command and Loop 33 completion state

- [x] **Step 1: Document explicit external connector prototype**

Document:

```bash
python3 scripts/external_connector_smoke.py --work-dir /tmp/skill2workflow-external-connector
```

State that external connectors are explicitly loaded local fixtures; automatic discovery and product-specific connectors remain out of scope.

- [x] **Step 2: Update Roadmap**

Move Loop 33 to complete and set Loop 34 Connector Packaging Boundary as the next active loop.

- [x] **Step 3: Verify docs**

Run:

```bash
git diff --check
```

Expected: no output.

### Task 5: Full Verification And PR

**Files:**
- No additional files.

**Interfaces:**
- Consumes: all Loop 33 changes
- Produces: draft PR

- [x] **Step 1: Run focused verification**

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors tests.test_control_plane tests.test_external_connector_smoke -v
python3 scripts/external_connector_smoke.py --work-dir /tmp/skill2workflow-external-connector-loop33
```

- [x] **Step 2: Run full verification**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

- [x] **Step 3: Commit and open draft PR**

```bash
git add README.md ROADMAP.md docs/connectors.md docs/examples.md docs/superpowers/plans/2026-07-07-connector-extension-prototype.md examples/connectors/local_echo_connector.py scripts/external_connector_smoke.py src/skill2workflow/connectors.py src/skill2workflow/control_plane.py src/skill2workflow/dashboard.py src/skill2workflow/executor.py src/skill2workflow/external_connectors.py src/skill2workflow/external_connector_smoke.py src/skill2workflow/storage.py tests/test_connectors.py tests/test_control_plane.py tests/test_external_connector_smoke.py tests/test_storage.py
git commit -m "feat: add connector extension prototype"
git push -u origin loop-33-connector-extension-prototype
```
