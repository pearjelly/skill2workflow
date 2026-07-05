# Credential Provider Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local credential-provider boundary so connector bindings can reference credential handles without storing secret values in Workflow DSL, trigger input, run state, or audit events.

**Architecture:** Add a small standard-library credential module with an in-memory static provider and JSON-file loader for local CLI runs. HTTP connector bindings may declare handle-based header credentials under `connector.credentials`; the executor passes a provider into connector execution, and resolved secret values are used only for the outbound request. Node results, run context, audit events, Workflow DSL fixtures, and LiteGraph fixtures retain handles only.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing JSON/SQLite storage and CLI.

---

### Task 1: Credential Provider Contract

**Files:**
- Create: `tests/test_credentials.py`
- Create: `src/skill2workflow/credentials.py`

- [x] **Step 1: Write failing provider tests**

Add tests for an in-memory provider and local credential file:

```python
provider = StaticCredentialProvider({"demo_api_token": "secret-token"})
self.assertEqual(provider.resolve("demo_api_token"), "secret-token")

with self.assertRaisesRegex(CredentialResolutionError, "credential handle not found: missing_token"):
    provider.resolve("missing_token")
```

Add file loading coverage:

```python
path.write_text(json.dumps({"credentials": {"demo_api_token": "secret-token"}}), encoding="utf-8")
provider = load_credential_file(path)
self.assertEqual(provider.resolve("demo_api_token"), "secret-token")
```

Reject invalid files:

```python
path.write_text(json.dumps({"credentials": ["bad"]}), encoding="utf-8")
with self.assertRaisesRegex(ValueError, "credentials must be an object"):
    load_credential_file(path)
```

- [x] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_credentials -v
```

Expected: fail because `skill2workflow.credentials` does not exist.

- [x] **Step 3: Implement provider module**

Create `src/skill2workflow/credentials.py` with:

```python
class CredentialResolutionError(Exception):
    ...

class StaticCredentialProvider:
    def __init__(self, credentials):
        ...

    def resolve(self, handle):
        ...

def load_credential_file(path):
    ...
```

Only string handles and string values are accepted. Missing handles raise `CredentialResolutionError` with the handle name only, never the secret value.

### Task 2: HTTP Connector Credential Handles

**Files:**
- Modify: `tests/test_connectors.py`
- Modify: `src/skill2workflow/connectors.py`

- [x] **Step 1: Write failing connector tests**

Add a test for `connector.credentials`:

```python
result = execute_connector(
    _credential_http_node(server.url("/success")),
    credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
)
self.assertEqual(server.requests[0]["headers"]["Authorization"], "Bearer secret-token")
self.assertNotIn("secret-token", json.dumps(result))
```

Use this connector shape:

```json
{
  "id": "http",
  "kind": "http",
  "request": {"url": "..."},
  "credentials": [
    {
      "target": "header",
      "name": "Authorization",
      "handle": "demo_api_token",
      "prefix": "Bearer "
    }
  ]
}
```

Add a missing-credential test:

```python
with self.assertRaisesRegex(ConnectorExecutionError, "credential handle not found: missing_token"):
    execute_connector(_credential_http_node("http://127.0.0.1:1/not-called", handle="missing_token"))
```

- [x] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors -v
```

Expected: fail because `execute_connector` has no `credential_provider` argument and HTTP credentials are not applied.

- [x] **Step 3: Implement HTTP credential injection**

Update connector execution to accept `credential_provider=None`. For HTTP bindings, apply `connector.credentials` entries before building the `urllib.request.Request`.

Supported credential entry fields:

| Field | Behavior |
| --- | --- |
| `target` | Required. Only `header` is supported in this loop. |
| `name` | Required HTTP header name. |
| `handle` | Required credential handle resolved by the provider. |
| `prefix` | Optional string prepended to the resolved value. |

Do not store resolved credential values in connector result output.

### Task 3: Executor And CLI Provider Wiring

**Files:**
- Modify: `tests/test_executor.py`
- Modify: `tests/test_cli.py`
- Modify: `src/skill2workflow/executor.py`
- Modify: `src/skill2workflow/control_plane.py`
- Modify: `src/skill2workflow/cli.py`

- [x] **Step 1: Write failing executor test**

Add a credential-bound HTTP workflow test:

```python
state = LocalExecutor(
    Path(tmp),
    credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
).run(workflow)
self.assertEqual(state["status"], "completed")
self.assertNotIn("secret-token", json.dumps(state["node_results"]))
self.assertEqual(server.requests[0]["headers"]["Authorization"], "Bearer secret-token")
```

- [x] **Step 2: Write failing CLI test**

Add a CLI run test using:

```bash
skill2workflow run workflow.json --state-dir <state> --credential-file credentials.json
```

with:

```json
{"credentials": {"demo_api_token": "secret-token"}}
```

Assert the local server receives the Authorization header and the printed run state does not contain `secret-token`.

- [x] **Step 3: Wire providers through runtime paths**

Add `credential_provider` to `LocalExecutor` and `LocalControlPlane`, and add `--credential-file` to `run`, `resume`, `run-published`, `trigger`, and `resume-published`.

### Task 4: Docs, Stability, And Roadmap

**Files:**
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `AGENTS.md`
- Modify: `docs/credential-boundary.md`
- Modify: `docs/connectors.md`
- Modify: `docs/stability.md`
- Modify: `ROADMAP.md`

- [x] **Step 1: Document credential file format**

Document:

```json
{
  "credentials": {
    "demo_api_token": "local-secret-value"
  }
}
```

and state that the file is local-only and must not be committed.

- [x] **Step 2: Document connector handle shape**

Document `connector.credentials` for HTTP header injection and emphasize that only handles belong in Workflow DSL.

- [x] **Step 3: Advance Roadmap**

Mark Loop 25 complete, make Loop 26 Local Webhook Adapter the next active loop, and update readiness notes.

### Task 5: Verification And PR

**Files:**
- All changed files

- [x] **Step 1: Run focused tests**

```bash
PYTHONPATH=src python3 -m unittest tests.test_credentials tests.test_connectors tests.test_executor tests.test_cli -v
```

- [x] **Step 2: Run full verification**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop25
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke-loop25
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

- [x] **Step 3: Commit, push, and open draft PR**

Commit with an intentional message, push `loop-25-credential-provider-interface`, open a draft PR, and monitor CI.
