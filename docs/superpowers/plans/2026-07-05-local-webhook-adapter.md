# Local Webhook Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dependency-free local webhook adapter that turns HTTP POST payloads into existing control-plane trigger requests.

**Architecture:** Keep `LocalControlPlane.trigger_workflow` as the only execution boundary. Add `src/skill2workflow/webhooks.py` as a thin normalization, adapter, and local HTTP server module; wire it into `skill2workflow.cli` through a local-only `webhook-server` command. Webhook input becomes trigger `input`; responses and audit events stay compact.

**Tech Stack:** Python 3.9 standard library, `unittest`, `http.server`, existing JSON/SQLite control-plane storage.

---

### Task 1: Webhook Request Contract

**Files:**
- Create: `tests/test_webhooks.py`
- Create: `src/skill2workflow/webhooks.py`

- [x] **Step 1: Write failing contract tests**

Add tests for `parse_webhook_request` that assert:
- `POST /webhooks/workflow_demo/0.1.0` with a JSON object maps to `workflow_id`, `version`, `source`, `idempotency_key`, and `input`
- absent `source` defaults to `local-webhook`
- non-POST requests, malformed paths, non-JSON bodies, and non-object input return deterministic `WebhookError` messages

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_webhooks -v
```

Expected: import failure for `skill2workflow.webhooks`.

- [x] **Step 3: Implement minimal request parsing**

Create `WebhookError` and `parse_webhook_request(method, path, body)` in `src/skill2workflow/webhooks.py`. Keep it pure and side-effect free.

- [x] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_webhooks -v
```

Expected: webhook parsing tests pass.

### Task 2: Control-Plane Adapter

**Files:**
- Modify: `tests/test_webhooks.py`
- Modify: `src/skill2workflow/webhooks.py`

- [x] **Step 1: Write failing adapter tests**

Add tests for `handle_webhook_request(control, method, path, body)` that:
- publish a workflow, invoke the adapter, and assert the response matches trigger output
- assert run context contains webhook input
- assert audit contains compact trigger metadata and no raw input payload
- repeat the happy path with SQLite storage
- exercise `serve_webhook_requests(..., once=True)` with a real local POST against an ephemeral port

- [x] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_webhooks -v
```

Expected: `handle_webhook_request` missing.

- [x] **Step 3: Implement the adapter**

Add `handle_webhook_request(control_plane, method, path, body)` that calls `parse_webhook_request`, then delegates to `control_plane.trigger_workflow`.

- [x] **Step 4: Run tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_webhooks -v
```

Expected: parsing and adapter tests pass.

### Task 3: Local CLI Server

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/skill2workflow/cli.py`
- Modify: `src/skill2workflow/webhooks.py`

- [x] **Step 1: Write failing CLI test**

Add a CLI test that:
- invokes `webhook-server` with `--host`, `--port`, `--state-dir`, `--storage`, and `--once`
- patches the server function so the test does not leave a long-running process behind
- asserts the command wires a `LocalControlPlane` with the requested state directory and server settings

- [x] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli -v
```

Expected: CLI rejects unknown command `webhook-server`.

- [x] **Step 3: Implement local server and CLI wiring**

Add `serve_webhook_requests(host, port, control_plane, once=False)` using `HTTPServer`. Wire `webhook-server` into the CLI with `--host`, `--port`, `--once`, `--state-dir`, `--storage`, and `--credential-file`.

- [x] **Step 4: Run CLI tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli -v
```

Expected: CLI tests pass.

### Task 4: Documentation And Verification

**Files:**
- Modify: `docs/triggers.md`
- Modify: `HARNESS.md`
- Modify: `ROADMAP.md`

- [x] **Step 1: Update docs**

Document:
- `POST /webhooks/<workflow_id>/<version>`
- request body with `source`, `idempotency_key`, and `input`
- local `webhook-server` command and `curl` example
- current limits: no auth, queue, hosted service, or secret storage

- [x] **Step 2: Update Roadmap status**

Mark Loop 26 complete in the completed loop table and make Loop 27 the next active priority.

- [x] **Step 3: Run full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
PYTHONPATH=src python3 -m unittest tests.test_triggers tests.test_control_plane tests.test_cli tests.test_webhooks -v
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all commands pass.

- [x] **Step 4: Publish the branch**

Commit, push, and open a draft PR with a summary of webhook adapter behavior, docs, and verification.
