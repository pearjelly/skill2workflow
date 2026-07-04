# Credential Boundary And Secret Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep committed Workflow DSL connector examples free of obvious secrets while documenting the credential boundary for future connector expansion.

**Architecture:** Add a dependency-free secret hygiene scanner that walks committed JSON fixtures and reports findings with file paths, JSON paths, and reasons. Expose it through a small script for CI and contributor use, keep Workflow DSL compatibility unchanged, and document allowed placeholder/local-test patterns instead of adding secret storage.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing GitHub Actions workflow.

---

### Task 1: Secret Hygiene Tests

**Files:**
- Create: `tests/test_secret_hygiene.py`
- Create: `src/skill2workflow/secret_hygiene.py`

- [x] **Step 1: Write failing scanner tests**

Add tests covering:

```python
from skill2workflow.secret_hygiene import scan_json_value

findings = scan_json_value({"headers": {"Authorization": "Bearer sk-live-secret"}}, source="workflow.json")
self.assertEqual(findings[0]["path"], "$.headers.Authorization")
```

and safe placeholders:

```python
findings = scan_json_value(
    {"headers": {"Authorization": "Bearer <redacted>", "X-API-Key": "example-token"}},
    source="workflow.json",
)
self.assertEqual(findings, [])
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_secret_hygiene -v
```

Expected: fail because `skill2workflow.secret_hygiene` does not exist yet.

- [x] **Step 3: Implement minimal scanner**

Create `src/skill2workflow/secret_hygiene.py` with:

```python
def scan_json_value(value, source="<memory>"):
    ...
```

The scanner should recurse through dictionaries and lists, flag obvious secret-like keys and values, and allow documented placeholders such as `<redacted>`, `REDACTED`, `placeholder`, and `example-token`.

- [x] **Step 4: Run focused scanner tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_secret_hygiene -v
```

Expected: pass.

### Task 2: Fixture And Script Guardrails

**Files:**
- Modify: `tests/test_secret_hygiene.py`
- Create: `scripts/secret_hygiene.py`
- Modify: `.github/workflows/ci.yml`

- [x] **Step 1: Add fixture and script tests**

Extend `tests/test_secret_hygiene.py` to assert:

```python
findings = scan_json_paths(sorted((ROOT / "examples" / "workflows").glob("*.json")))
self.assertEqual(findings, [])
```

and verify the script exits non-zero for a temporary JSON file containing:

```json
{"connector": {"request": {"headers": {"Authorization": "Bearer sk-live-secret"}}}}
```

- [x] **Step 2: Run tests to verify script behavior fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_secret_hygiene -v
```

Expected: fail because `scripts/secret_hygiene.py` and path scanning are not implemented yet.

- [x] **Step 3: Implement script and CI check**

Create `scripts/secret_hygiene.py` so contributors can run:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

The script should print JSON output, return `0` when no findings exist, and return `1` when findings exist. Add the same command to `.github/workflows/ci.yml`.

- [x] **Step 4: Run focused tests and script**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_secret_hygiene -v
python3 scripts/secret_hygiene.py examples/workflows
```

Expected: both pass.

### Task 3: Credential Boundary Docs

**Files:**
- Create: `docs/credential-boundary.md`
- Modify: `docs/connectors.md`
- Modify: `docs/workflow-dsl-compatibility.md`
- Modify: `CONTRIBUTING.md`
- Modify: `HARNESS.md`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `ROADMAP.md`

- [x] **Step 1: Document safe patterns**

Create `docs/credential-boundary.md` explaining:

- Workflow DSL fixtures must not contain real secrets
- allowed example values include local URLs, empty values, `<redacted>`, `REDACTED`, `placeholder`, and `example-token`
- unsupported current behavior includes secret storage, token injection, redaction at runtime, RBAC, IAM, and product-specific SaaS credentials
- future credential provider work must keep secret material outside immutable Workflow DSL artifacts

- [x] **Step 2: Wire docs and roadmap**

Update connector, compatibility, contributor, harness, README, and AGENTS references. Mark Loop 22 complete in `ROADMAP.md` and set Loop 23 to a small next loop focused on trigger/local run API work.

### Task 4: Verification And PR

**Files:**
- Modify: `docs/superpowers/plans/2026-07-04-credential-boundary-secret-hygiene.md`

- [x] **Step 1: Run final verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop22
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all pass.

- [x] **Step 2: Commit, push, and open draft PR**

Use:

```bash
git add .
git commit -m "feat: add connector secret hygiene guardrails"
git push -u origin loop-22-credential-boundary-secret-hygiene
gh pr create --draft --title "feat: add connector secret hygiene guardrails" --body-file /tmp/skill2workflow-loop22-pr.md
```
