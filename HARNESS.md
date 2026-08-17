# Project Harness

This file describes the executable project harness for the current open-source bootstrap.

## Local Verification

Run all tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Run the first-run contributor demo:

```bash
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo
python3 -m json.tool /tmp/skill2workflow-demo/artifacts/control-plane-snapshot.json >/tmp/skill2workflow-demo-snapshot-check.json
```

Open the local control-plane inspector at `http://localhost:4173/web/control.html` after starting `python3 -m http.server 4173`, then load `/tmp/skill2workflow-demo/artifacts/control-plane-snapshot.json`.
Use the Nodes tab to inspect compact run/audit overlays for each workflow node.

Run the local pilot playbook smoke:

```bash
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot
python3 -m json.tool /tmp/skill2workflow-pilot/artifacts/control-plane-snapshot.json >/tmp/skill2workflow-pilot-snapshot-check.json
python3 -m json.tool /tmp/skill2workflow-pilot/artifacts/workflow.overlay.litegraph.json >/tmp/skill2workflow-pilot-overlay-check.json
```

The pilot smoke exercises webhook trigger, durable input context, manual gate resume, local HTTP connector execution, credential-handle resolution, audit export, snapshot node overlays, and LiteGraph run overlays without using external services.

Published workflows may also declare a bounded `input_schema` contract. The
control plane validates it before idempotency claims and execution; see
[`docs/workflow-dsl-contract.md`](docs/workflow-dsl-contract.md) and
[`docs/triggers.md`](docs/triggers.md).

The self-hosted service also applies a fixed 16-handler process-local
admission budget to non-probe routes. Exhaustion returns a fixed `429` with
`Retry-After: 1`; `/healthz` and `/readyz` remain available for traffic
management. See [`docs/service.md`](docs/service.md).

Published workflow reads are integrity-checked against the control-plane
checksum before promotion, trigger validation, idempotency claims, or
execution. Missing or changed artifacts fail closed with fixed redacted errors;
see [`docs/published-artifact-integrity.md`](docs/published-artifact-integrity.md).

Before moving a stable alias, operators can use `workflow-diff` for a bounded
structural review and pass `--expected-current-version` to `promote` for an
optimistic-concurrency check. The diff contains checksums and structural
identifiers, never workflow content; see [`docs/workflow-releases.md`](docs/workflow-releases.md).
SQLite-backed promotion performs that check, the alias mutation, and the
`workflow_promoted` audit append in one transaction; concurrent stale
promotions therefore fail without changing the alias or audit chain. JSON
storage remains intended for local evaluation and does not provide
cross-process transaction coordination.

SQLite publication and deprecation also use single-record transactions: a
published version and its audit row commit together, distinct concurrent
versions cannot erase each other, and same-version matching retries are
idempotent. See [`docs/workflow-releases.md`](docs/workflow-releases.md).
The `workflow-artifacts` command adds a bounded, value-free consistency report
for missing, unsafe, mismatched, invalid, oversized, and orphaned files; known
SQLite publication failures clean up only still-unregistered matching files.
The `audit-consistency` command compares durable run-state event counts with
control-plane audit counts, and lifecycle/runtime audit batches are emitted in
one control-store transaction. The two SQLite databases remain a deliberate
cross-database recovery boundary.

Run the local scheduled-trigger smoke:

```bash
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop29
python3 -m json.tool /tmp/skill2workflow-schedule-loop29/artifacts/control-plane-snapshot.json >/tmp/skill2workflow-schedule-snapshot-check.json
```

The schedule smoke exercises a deterministic one-shot schedule, due-run selection with an explicit timestamp, the published trigger boundary, durable input context, audit export, and control-plane snapshot generation without cron, sleeping, background threads, or external services.

Run the durable recurring scheduler evidence:

```bash
python3 scripts/recurring_scheduler_smoke.py --work-dir /tmp/skill2workflow-recurring-scheduler-loop43
python3 -m json.tool /tmp/skill2workflow-recurring-scheduler-loop43/recurring-scheduler-smoke.json >/tmp/skill2workflow-recurring-scheduler-check.json
```

This real-process smoke covers recurring dispatch, restart recovery, `latest` missed-run coalescing, single-owner readiness, active/standby lease takeover, stale-claim `uncertain` recovery, and graceful exit. It uses only local SQLite and loopback listeners.

Run the verified backup/restore drill:

```bash
python3 scripts/backup_restore_smoke.py --work-dir /tmp/skill2workflow-backup-restore-loop44
python3 -m json.tool /tmp/skill2workflow-backup-restore-loop44/backup-restore-smoke.json >/tmp/skill2workflow-backup-restore-check.json
```

The drill proves offline lease exclusion, a verified point-in-time snapshot, atomic restore, restored-service readiness and trigger execution, tamper rejection, credential exclusion, and graceful shutdown.

Create and verify a portable Workflow DSL bundle without executing it:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-create \
  examples/workflows/approval-flow.workflow.json \
  --output /tmp/skill2workflow-approval.s2w
PYTHONPATH=src python3 -m skill2workflow.cli bundle-verify \
  /tmp/skill2workflow-approval.s2w
PYTHONPATH=src python3 -m skill2workflow.cli bundle-diff \
  /tmp/skill2workflow-approval-old.s2w \
  /tmp/skill2workflow-approval-new.s2w
PYTHONPATH=src python3 -m skill2workflow.cli bundle-preflight \
  /tmp/skill2workflow-approval.s2w \
  --format text
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/skill2workflow-approval.s2w \
  --state-dir /tmp/skill2workflow-bundle-run \
  --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli bundle-publish \
  /tmp/skill2workflow-approval.s2w \
  --state-dir /tmp/skill2workflow-control \
  --storage sqlite
```

The bundle path is deterministic and secret-checked; verification is bounded,
read-only, and does not extract or execute either member. Publication performs
the same verification before entering the normal immutable local control-plane
path. See
[`docs/workflow-bundles.md`](docs/workflow-bundles.md).

Run the state upgrade/migration evidence:

```bash
python3 scripts/state_upgrade_smoke.py --work-dir /tmp/skill2workflow-state-upgrade-loop45
python3 -m json.tool /tmp/skill2workflow-state-upgrade-loop45/state-upgrade-smoke.json >/tmp/skill2workflow-state-upgrade-check.json
```

The drill proves read-only legacy preflight, a verified pre-upgrade backup, source immutability, atomic copy-on-write publication, upgraded-service readiness and trigger execution, future-layout rejection, and graceful shutdown.

Run the authenticated observability evidence:

```bash
python3 scripts/observability_smoke.py --work-dir /tmp/skill2workflow-observability-loop46
python3 scripts/observability_rules_smoke.py
python3 scripts/observability_dashboard_smoke.py
python3 -m json.tool /tmp/skill2workflow-observability-loop46/observability-smoke.json >/tmp/skill2workflow-observability-check.json
```

This real-process smoke proves default-deny metrics, authenticated Prometheus text export, aggregate workflow/run state, fixed low-cardinality labels, private-value exclusion, and structured lifecycle/request NDJSON. The companion rules and dashboard smokes check the operator-managed alert and Grafana starter packs without requiring Prometheus/Grafana or adding runtime dependencies.

Run the data retention/disposal evidence:

```bash
python3 scripts/retention_smoke.py --work-dir /tmp/skill2workflow-retention-loop47
python3 -m json.tool /tmp/skill2workflow-retention-loop47/retention-smoke.json >/tmp/skill2workflow-retention-check.json
```

Run the durable cooperative cancellation evidence:

```bash
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-cancellation-loop48
python3 -m json.tool /tmp/skill2workflow-cancellation-loop48/cancellation-smoke.json >/tmp/skill2workflow-cancellation-check.json
```

Verify the authenticated human-gate decision route:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_authenticated_resume_endpoint_requires_exact_decision_and_reuses_audit_path \
  -v
```

The route contract, exact decision body, fixed errors, and external TLS
boundary are documented in [`docs/human-approval.md`](docs/human-approval.md).

The installed CLI can perform the same actions without exposing a token in
argv:

```bash
skill2workflow service-resume <run_id> \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
skill2workflow service-cancel <run_id> \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
skill2workflow service-show <run_id> \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-runs \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-run-page \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --status failed \
  --max-items 25

skill2workflow service-recurring-schedules \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-recurring-dispatches \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --schedule-id schedule_hourly_report

skill2workflow service-workflow-artifacts \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-backup-readiness \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-backup-inventory \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --max-items 25

skill2workflow service-backup-inventory-page \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --max-items 25 \
  --cursor <next_cursor-from-the-previous-page>

skill2workflow service-backup-retention-plan /etc/skill2workflow/backup-retention.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-retention-readiness /etc/skill2workflow/retention.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-operational-readiness \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-audit-integrity \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-runtime-info \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-workflow-publish /path/to/workflow.workflow.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-workflow-promote workflow_approval_flow \
  --version 0.2.0 --alias production \
  --expected-current-version 0.1.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-workflow-deprecate workflow_approval_flow \
  --version 0.1.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-workflows \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-workflow-diff workflow_approval_flow \
  --from-version 0.1.0 --to-version 0.2.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-token-rotate \
  --config /srv/skill2workflow/config/service.json

skill2workflow service-trigger workflow_approval_flow \
  --version production \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --idempotency-key partner-event-001 \
  --input /path/to/non-secret-input.json

skill2workflow service-schedule-disable schedule_hourly_report \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
skill2workflow service-schedule-enable schedule_hourly_report \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-audit-consistency \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-audit-events \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --max-items 100

skill2workflow service-support-bundle \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --output /var/lib/skill2workflow/support-bundle.json
```

For an unauthenticated live cutover gate, use the bounded service probe:

```bash
skill2workflow service-probe --service-url https://service.example
```

The local `service-token-rotate` command replaces the owner-only ingress token
atomically without printing it or restarting the service. See
[`docs/service-token-rotation.md`](docs/service-token-rotation.md) for the
secret-handling boundary.

Run the interrupted-run crash recovery evidence:

```bash
python3 scripts/interrupted_recovery_smoke.py --work-dir /tmp/skill2workflow-interrupted-loop49
python3 -m json.tool /tmp/skill2workflow-interrupted-loop49/interrupted-recovery-smoke.json >/tmp/skill2workflow-interrupted-check.json
```

Run the secure first-service bootstrap evidence:

```bash
python3 scripts/service_bootstrap_smoke.py --work-dir /tmp/skill2workflow-service-bootstrap-loop51
```

Run the installed controlled quickstart evidence:

```bash
python3 scripts/quickstart_smoke.py --work-dir /tmp/skill2workflow-quickstart-loop52
```

This real-process smoke proves active-service refusal, source preservation, fixed old-terminal deletion, waiting/claimed protection, byte-level private-payload removal from the retained databases, and retained-service cutover.

Run the isolated wheel and console-script smoke:

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```

The package smoke also writes a value-free release artifact manifest with the
wheel and member SHA-256 hashes under that work directory.

On Linux, verify the generated supervisor with the host's real systemd parser
without installing or starting it:

```bash
python3 scripts/systemd_service_smoke.py \
  --work-dir /tmp/skill2workflow-systemd-service-linux \
  --systemd-analyze-verify
```

Run the committed-fixture secret hygiene check:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

Manual editable install path:

```bash
python3 -m venv /tmp/skill2workflow-venv
/tmp/skill2workflow-venv/bin/python -m pip install --upgrade pip "setuptools>=77.0.1"
/tmp/skill2workflow-venv/bin/python -m pip install --no-build-isolation -e .
/tmp/skill2workflow-venv/bin/skill2workflow validate examples/workflows/approval-flow.workflow.json --format json
```

Run the CLI closed loop:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json --run-state /tmp/skill2workflow-state/runs/<run_id>.json -o /tmp/skill2workflow-overlay.litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/http-connector.workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/http-connector.workflow.json -o examples/workflows/http-connector.litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
```

The sample workflow pauses at a human approval gate. Resume it with:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli resume <run_id> --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli resume <run_id> --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
```

List summaries and inspect full run logs:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-state --limit 100
PYTHONPATH=src python3 -m skill2workflow.cli show <run_id> --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite --limit 100
PYTHONPATH=src python3 -m skill2workflow.cli show <run_id> --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
```

The optional `--limit` keeps local run inspection to the newest 1-1000 compact
summaries; omit it to preserve the complete-list path. See
[`docs/run-list.md`](docs/run-list.md) for ordering and storage-boundary details.

Open the LiteGraph editor:

```bash
python3 -m http.server 4173
```

Then visit `http://localhost:4173/web/`.

Run the minimal control plane closed loop:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli workflows --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli workflows --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli workflow-artifacts --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli audit-consistency --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli workflow workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
printf '{"credentials":{"demo_api_token":"local-secret-value"}}' >/tmp/skill2workflow-credentials.json
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state --credential-file /tmp/skill2workflow-credentials.json
printf '{"customer_id":"customer_123"}' >/tmp/skill2workflow-trigger-input.json
PYTHONPATH=src python3 -m skill2workflow.cli trigger workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control --source local-cli --idempotency-key example-001 --input /tmp/skill2workflow-trigger-input.json
cat >/tmp/skill2workflow-schedule.json <<'JSON'
{"schema_version":"skill2workflow-schedule-0.1.0","schedule":{"id":"schedule_approval_flow_daily","workflow_id":"workflow_approval_flow","version":"0.1.0","run_at":"2026-07-06T00:00:00Z"},"trigger":{"input":{"customer_id":"customer_123"}}}
JSON
PYTHONPATH=src python3 -m skill2workflow.cli schedule-add /tmp/skill2workflow-schedule.json --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli schedules --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli schedule-run-due --state-dir /tmp/skill2workflow-control --now 2026-07-06T00:00:00Z
PYTHONPATH=src python3 -m skill2workflow.cli resume-published <run_id> --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli resume-published <run_id> --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli control-runs --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli control-run <run_id> --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --run-id <run_id> --event-type run_completed
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --run-id <run_id> --event-type connector_completed
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_retrying
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_recovered
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli audit-verify --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli backup-list --parent-dir /var/backups/skill2workflow --limit 100
PYTHONPATH=src python3 -m skill2workflow.cli backup-retention-plan /etc/skill2workflow/backup-retention.json --parent-dir /var/backups/skill2workflow
PYTHONPATH=src python3 -m skill2workflow.cli workflows --state-dir /tmp/skill2workflow-control --storage sqlite --limit 100
PYTHONPATH=src python3 -m skill2workflow.cli schedules --state-dir /tmp/skill2workflow-control --storage sqlite --limit 100
PYTHONPATH=src python3 -m skill2workflow.cli schedule-dispatches --state-dir /tmp/skill2workflow-control --storage sqlite --limit 100
PYTHONPATH=src python3 -m skill2workflow.cli schedule-run-due --state-dir /tmp/skill2workflow-control --storage sqlite --now 2026-08-14T00:00:00Z --max-items 25
PYTHONPATH=src python3 -m skill2workflow.cli connectors --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json
PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --service-url http://127.0.0.1:8080 --auth-token-file /tmp/skill2workflow-ingress.token -o /tmp/skill2workflow-live-snapshot.json
```

Open the local control-plane inspector at `http://localhost:4173/web/control.html` after starting `python3 -m http.server 4173`.

Snapshot run summaries include read-only `node_overlays` keyed by Workflow DSL node id. They contain status, current-node marker, event count, latest event type, connector outcome, attempts, retry/recovery flags, and audit event counts. They intentionally omit raw connector output, resolved credentials, authorization headers, raw webhook bodies, and full trigger input values.

Run a local webhook adapter smoke after publishing the workflow.

Terminal 1:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli webhook-server --state-dir /tmp/skill2workflow-control --host 127.0.0.1 --port 8080
```

Terminal 2:

```bash
curl -sS -X POST http://127.0.0.1:8080/webhooks/workflow_approval_flow/0.1.0 -H 'Content-Type: application/json' -d '{"source":"local-webhook","idempotency_key":"example-001","input":{"customer_id":"customer_123"}}'
```

## Current Scope

Implemented:

- Parser
  - frontmatter extraction
  - hard gate extraction
  - checklist normalization
  - structured step details with source line numbers
  - fenced-code exclusion for rule hints
- Compiler
  - compiles ordered step details into node titles, descriptions, and source metadata
  - generates start, ordered step, failure, and end nodes
  - generates success and failure edges
- Validator
  - documents Workflow DSL `0.1.0` with `schemas/workflow.schema.json`
  - exposes structured validation errors through `validate_workflow_structured`
  - supports `validate --format json` for tool and UI integrations
  - checks node ids and edge ids
  - checks edge endpoint references
  - checks terminal nodes have no outgoing transition
  - checks node transitions have matching edges
  - checks edges are declared by node transitions
  - requires `tool_call` nodes to declare `connector.id`
- Durable local executor
  - supports JSON file run storage by default
  - supports opt-in SQLite run storage through `--storage sqlite`
  - stores queryable run event rows in SQLite
  - records terminal node results
  - records human gate approvals and rejections
  - supports rejected human gate failure paths
  - executes connector-bound `tool_call` nodes through the built-in HTTP connector
  - honors `retry.max_attempts` and `policies.default_retry.max_attempts` for connector nodes
  - records connector start, completion, and failure events in run state
  - records `node_retrying`, `node_recovered`, and `node_failed` runtime policy events for local recovery inspection
  - exposes run summaries and full run details
- LiteGraph visualization
  - converts Workflow DSL into LiteGraph-compatible graph JSON
  - embeds source Workflow DSL in generated LiteGraph JSON for safe write-back
  - preserves workflow node ids, node types, descriptions, source metadata, and run status
  - attaches read-only run overlay evidence when `visualize --run-state` is used
  - includes connector metadata in node properties for inspection
  - includes a static web editor that loads Workflow DSL or LiteGraph JSON
  - exposes node parameters in an inspector
  - provides an example workflow gallery
  - supports simple title and description edits in the LiteGraph view
  - supports safe action, retry, and HTTP connector request edits in the LiteGraph view
  - writes title and description edits back to Workflow DSL without changing topology
  - writes allowlisted authoring fields back to Workflow DSL without changing connector identity
  - marks invalid graph connections in the UI
- Minimal local control plane
  - publishes immutable workflow artifacts
  - promotes published versions behind bounded control-plane aliases such as `production`
  - compares exact published versions through the bounded `workflow-diff` review contract
  - reports registry/file consistency through bounded `workflow-artifacts` diagnostics
  - reports run-state/control-audit divergence through bounded `audit-consistency` diagnostics
  - exposes the same diagnostic through authenticated `service-audit-consistency` for remote operators
  - exposes a bounded, redacted chronological audit tail through authenticated `service-audit-events`
  - exposes durable recurring schedule timing and state through authenticated `service-recurring-schedules` and controlled enable/disable actions through `service-schedule-enable`/`service-schedule-disable`
  - supports an optional expected-current-version compare-and-swap promotion guard
  - tracks draft, published, and deprecated lifecycle state through JSON or SQLite registry storage
  - runs published workflow versions
  - triggers published workflow versions or stable aliases through a compact local API envelope
  - serves local webhook POST requests through the same published trigger boundary
  - runs deterministic one-shot local schedules through the same published trigger boundary
  - resumes waiting published runs
  - lists and shows run state through control-plane commands
  - keeps run state bound to workflow id and version
  - records workflow publish, promote, deprecate, and run events in JSONL or SQLite audit storage
  - adds trigger metadata to `run_started` audit events for triggered runs
  - filters audit events by workflow id, version, run id, and event type
  - verifies the current SQLite audit chain with the payload-free `audit-verify` command
  - records connector execution events in audit storage for published runs
  - promotes runtime policy events such as retry and recovery into audit storage for published runs
  - imports existing JSON registry and audit files when opening SQLite control-plane storage
  - exposes built-in connector manifests
  - exports a read-only local operator snapshot through `control-snapshot`
  - derives operator insights for attention items, recent events, connector events, and version changes
  - derives compact per-node run overlays from run state and promoted audit events
  - provides a static control-plane inspector for operator insights, node overlays, workflows, runs, audit events, connectors, and version comparisons
- Demo onboarding
  - generates a resettable local demo workspace through `scripts/demo_bootstrap.py`
  - writes Workflow DSL, LiteGraph, and control-plane snapshot artifacts under the demo work directory
  - exercises parse, compile, validate, publish, run, resume, audit, and snapshot paths without network access or secrets
- Pilot playbook
  - generates a resettable local pilot workspace through `scripts/pilot_playbook_smoke.py`
  - exercises webhook trigger, manual gate resume, HTTP connector execution, credential handles, audit, snapshot, and LiteGraph overlay artifacts
  - documents the supported local pilot boundary in `docs/pilot-playbook.md`
- Scheduled trigger smoke
  - generates a resettable local schedule workspace through `scripts/schedule_smoke.py`
  - exercises schedule definition, due-run selection, published trigger execution, manual gate resume, audit, and snapshot artifacts
  - documents the schedule contract and non-goals in `docs/triggers.md`
- Packaging and installability
  - verifies package metadata and empty runtime dependency policy through `tests/test_packaging.py`
  - builds a wheel, installs it into a separate virtual environment, clears source-import paths, and verifies the installed `skill2workflow` console script, service help, production-module imports, and workflow validation through `scripts/package_smoke.py`
  - keeps source-checkout `PYTHONPATH=src` commands and editable-install commands documented side by side
- Secure service bootstrap
  - creates a complete non-overwriting owner-only service workspace through `skill2workflow service-init`
  - generates the ingress secret without printing it and wires absolute config, state, and connector paths
  - proves unchanged startup, readiness, authentication, no-overwrite behavior, graceful exit, and durable state through `scripts/service_bootstrap_smoke.py`
- Linux systemd supervision
  - generates one non-overwriting, manually reviewed Linux service unit through `skill2workflow systemd-unit`
  - fixes least-privilege state-only write access, process sandboxing, restart behavior, and SIGTERM-only shutdown without embedding credential values
  - proves CLI generation, Doctor compatibility, static hardening directives, redaction, permissions, and no-overwrite behavior through `scripts/systemd_service_smoke.py`
- Installed controlled quickstart
  - compiles a bundled standard Skill and publishes it immutably through the installed `quickstart` command
  - creates a durable waiting run that completes after one explicit approval
  - proves the wheel-only journey, generated service startup, and authenticated second trigger through `scripts/quickstart_smoke.py`
- Connector runtime
  - provides active `manual` and `http` connector manifests
  - gives compiled `human_gate` nodes a default manual connector binding
  - gives compiled `tool_call` nodes a default HTTP connector binding
  - executes HTTP requests with the Python standard library
  - resolves local credential handles for HTTP connector request headers through `--credential-file`
  - maps non-secret trigger input into HTTP request body fields through `connector.request.input_mapping`
  - exposes a documented connector manifest contract for future extension packages
  - covers HTTP connector success, HTTP error, invalid request metadata, JSON body, headers, and timeout behavior with deterministic local tests
  - documents retry, timeout, and credential boundaries in `docs/connectors.md`
- Credential boundary and secret hygiene
  - documents safe connector example patterns in `docs/credential-boundary.md`
  - checks committed Workflow DSL and LiteGraph example fixtures for obvious secret-like values through `scripts/secret_hygiene.py`
  - keeps real secrets, redaction, IAM, and SaaS credential flows outside immutable Workflow DSL artifacts
  - keeps resolved credential values out of run state and audit events in the built-in runtime
- Local trigger API
  - documents the trigger request and response envelope in `docs/triggers.md`
  - exposes `trigger` as a CLI path for starting published workflow runs
  - exposes `schedule-add`, `schedules`, and `schedule-run-due` for deterministic local schedule evaluation
  - records trigger id, source, idempotency key, and input keys in compact responses and audit events
  - persists trigger input values under `run_state.context.input`
  - exposes compact trigger metadata under `run_state.context.trigger`
  - shares one mapping behavior across CLI, webhook, and scheduled-trigger runs
  - enforces one 1 MiB canonical UTF-8 input limit across CLI, webhook, one-shot, and recurring schedule triggers
  - bounds advertised HTTP request-body reads to five seconds and returns fixed `408` errors for stalled clients
- Runtime policy and recovery
  - documents retry and recovery semantics in `docs/runtime-policy.md`
  - treats `retry.max_attempts` as retries after the first connector attempt
  - keeps global deadlines, delayed backoff, compensation, queues, and credential management outside the current local runtime boundary
- Open-source release readiness
  - documents contributor setup and PR expectations in `CONTRIBUTING.md`
  - provides GitHub issue templates for bugs, feature requests, and workflow examples
  - documents first release scope in `docs/releases/v0.1.0.md`
  - documents Workflow DSL `0.1.0` compatibility in `docs/workflow-dsl-compatibility.md`
  - documents stable and experimental surfaces in `docs/stability.md`
- CLI
- Tests
- Example Skill

Not implemented yet:

- Production-grade enterprise control plane UI
- Header/URL connector mapping, arbitrary input templating, expression engines, and schema-driven input mapping beyond the explicit body-only contract
- Hosted credential stores, credential encryption, IAM, and runtime redaction
- GitHub release automation
