# Connector Extension Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Define and test a dependency-free connector extension contract that future product-specific connectors can follow without adding a dynamic plugin loader in this loop.

**Architecture:** Treat built-in `manual` and `http` connectors as reference manifests. Add stable manifest metadata and a small validator in `src/skill2workflow/connectors.py`; document execution handoff, credential, and audit rules in public docs.

**Tech Stack:** Python 3.9 standard library, `unittest`, Markdown documentation.

---

### Task 1: Manifest Contract Tests

**Files:**
- Modify: `tests/test_connectors.py`
- Modify: `src/skill2workflow/connectors.py`

- [x] **Step 1: Write failing manifest contract tests**

Add imports:

```python
from skill2workflow.connectors import (
    CONNECTOR_MANIFEST_VERSION,
    ConnectorExecutionError,
    _timeout_seconds,
    default_connectors,
    execute_connector,
    validate_connector_manifest,
)
```

Add tests:

```python
def test_default_connector_manifests_follow_extension_contract(self):
    for manifest in default_connectors():
        with self.subTest(connector=manifest["id"]):
            self.assertEqual(validate_connector_manifest(manifest), [])
            self.assertEqual(manifest["manifest_version"], CONNECTOR_MANIFEST_VERSION)
            self.assertIn("execution_contract", manifest)
            self.assertIn("credential_contract", manifest)
            self.assertIn("audit_contract", manifest)


def test_validate_connector_manifest_reports_contract_gaps(self):
    errors = validate_connector_manifest(
        {
            "id": "",
            "kind": "http",
            "status": "active",
            "node_types": "tool_call",
            "config_schema": [],
            "execution_contract": {"mode": "dynamic"},
            "credential_contract": {"supports_handles": "yes"},
            "audit_contract": {"value_policy": ""},
        }
    )

    self.assertIn("manifest_version must be skill2workflow-connector-0.1.0", errors)
    self.assertIn("id is required", errors)
    self.assertIn("node_types must be a non-empty list", errors)
    self.assertIn("config_schema must be an object", errors)
    self.assertIn("execution_contract.mode must be built_in or external", errors)
    self.assertIn("credential_contract.supports_handles must be a boolean", errors)
    self.assertIn("audit_contract.value_policy is required", errors)
```

- [x] **Step 2: Run tests to verify red**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors.ConnectorTests.test_default_connector_manifests_follow_extension_contract tests.test_connectors.ConnectorTests.test_validate_connector_manifest_reports_contract_gaps -v
```

Expected: import failure for `CONNECTOR_MANIFEST_VERSION` or `validate_connector_manifest`.

- [x] **Step 3: Implement minimal contract metadata and validator**

In `src/skill2workflow/connectors.py`, add:

```python
CONNECTOR_MANIFEST_VERSION = "skill2workflow-connector-0.1.0"
CONNECTOR_EXECUTION_CONTRACT_VERSION = "skill2workflow-connector-execution-0.1.0"
```

Add `manifest_version`, `execution_contract`, `credential_contract`, and `audit_contract` to built-in connector manifests.

Add:

```python
def validate_connector_manifest(manifest: object) -> List[str]:
    errors = []
    if not isinstance(manifest, dict):
        return ["connector manifest must be an object"]
    if manifest.get("manifest_version") != CONNECTOR_MANIFEST_VERSION:
        errors.append(f"manifest_version must be {CONNECTOR_MANIFEST_VERSION}")
    if not str(manifest.get("id") or ""):
        errors.append("id is required")
    if not str(manifest.get("kind") or ""):
        errors.append("kind is required")
    node_types = manifest.get("node_types")
    if not isinstance(node_types, list) or not node_types:
        errors.append("node_types must be a non-empty list")
    if not isinstance(manifest.get("config_schema"), dict):
        errors.append("config_schema must be an object")
    execution_contract = manifest.get("execution_contract")
    if not isinstance(execution_contract, dict):
        errors.append("execution_contract must be an object")
    else:
        if execution_contract.get("contract_version") != CONNECTOR_EXECUTION_CONTRACT_VERSION:
            errors.append(f"execution_contract.contract_version must be {CONNECTOR_EXECUTION_CONTRACT_VERSION}")
        if execution_contract.get("mode") not in ("built_in", "external"):
            errors.append("execution_contract.mode must be built_in or external")
        if not isinstance(execution_contract.get("receives"), list) or not execution_contract.get("receives"):
            errors.append("execution_contract.receives must be a non-empty list")
        if not isinstance(execution_contract.get("returns"), list) or not execution_contract.get("returns"):
            errors.append("execution_contract.returns must be a non-empty list")
    credential_contract = manifest.get("credential_contract")
    if not isinstance(credential_contract, dict):
        errors.append("credential_contract must be an object")
    elif not isinstance(credential_contract.get("supports_handles"), bool):
        errors.append("credential_contract.supports_handles must be a boolean")
    audit_contract = manifest.get("audit_contract")
    if not isinstance(audit_contract, dict):
        errors.append("audit_contract must be an object")
    elif not str(audit_contract.get("value_policy") or ""):
        errors.append("audit_contract.value_policy is required")
    return errors
```

- [x] **Step 4: Run tests to verify green**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors.ConnectorTests.test_default_connector_manifests_follow_extension_contract tests.test_connectors.ConnectorTests.test_validate_connector_manifest_reports_contract_gaps -v
```

Expected: both tests pass.

### Task 2: Registry Exposure Test

**Files:**
- Modify: `tests/test_control_plane.py`

- [x] **Step 1: Write failing registry exposure assertion**

Extend `test_connector_registry_returns_active_connector_manifests`:

```python
self.assertEqual(http_connector["manifest_version"], "skill2workflow-connector-0.1.0")
self.assertEqual(http_connector["execution_contract"]["mode"], "built_in")
self.assertEqual(http_connector["credential_contract"]["supports_handles"], True)
self.assertEqual(http_connector["audit_contract"]["value_policy"], "compact_no_payload_values")
```

- [x] **Step 2: Run test**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_plane.ControlPlaneTests.test_connector_registry_returns_active_connector_manifests -v
```

Expected before implementation: key error for `manifest_version`.

- [x] **Step 3: Verify green after Task 1 implementation**

Run the same command again.

Expected: test passes.

### Task 3: Public Documentation

**Files:**
- Modify: `docs/connectors.md`
- Modify: `docs/credential-boundary.md`
- Modify: `docs/stability.md`
- Modify: `docs/workflow-dsl-compatibility.md`
- Modify: `CONTRIBUTING.md`
- Modify: `ROADMAP.md`

- [x] **Step 1: Document connector extension contract**

Add a `Connector Extension Contract` section to `docs/connectors.md` that defines manifest fields, execution handoff, normalized results, audit-safe summaries, and explicit non-goals.

- [x] **Step 2: Document credential rules**

Add extension connector requirements to `docs/credential-boundary.md`: use handles, never commit resolved values, never put secrets in trigger input or mapped payload values, and keep audit compact.

- [x] **Step 3: Update stability and compatibility docs**

Mark the minimum connector manifest contract as stable for `0.1.x`; keep dynamic loading and product-specific packages experimental/out of scope.

- [x] **Step 4: Update contributor guidance**

Point connector contributors to `docs/connectors.md` and require manifest contract tests plus secret hygiene checks.

- [x] **Step 5: Mark Loop 31 complete and Loop 32 next**

Move Loop 31 into completed loops in `ROADMAP.md`, set Loop 32 as active, and keep product-specific SaaS connectors deferred.

### Task 4: Verification And PR

**Files:**
- No new source files.

- [x] **Step 1: Run focused tests**

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors tests.test_control_plane -v
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
git add CONTRIBUTING.md ROADMAP.md docs/connectors.md docs/credential-boundary.md docs/stability.md docs/workflow-dsl-compatibility.md docs/superpowers/plans/2026-07-06-connector-extension-contract.md src/skill2workflow/connectors.py tests/test_connectors.py tests/test_control_plane.py
git commit -m "docs: define connector extension contract"
git push -u origin loop-31-connector-extension-contract
```
