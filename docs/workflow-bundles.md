# Workflow Bundles

Workflow bundles provide a small, portable way to share and review one
Workflow DSL artifact. A bundle is a deterministic ZIP archive containing
exactly two files:

- `workflow.json`: the validated Workflow DSL document;
- `manifest.json`: the fixed `skill2workflow-workflow-bundle-0.1.0` manifest,
  including the workflow digest, size, status, and connector IDs.

The bundle is a distribution format, not a second execution authority. The
runtime still validates and executes Workflow DSL, and a bundle never contains
credentials, resolved connector values, run state, or audit history.

## Create, verify, and publish

Create a bundle from a local Workflow DSL file:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-create \
  examples/workflows/approval-flow.workflow.json \
  --output /tmp/approval-flow.s2w
```

Creation validates the workflow and runs the repository's secret-hygiene
scanner. Existing output is not overwritten unless `--force` is supplied;
replacement is assembled in a temporary sibling and committed atomically.

Verify a bundle before importing or reviewing it:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-verify \
  /tmp/approval-flow.s2w
```

Verification is read-only and does not extract files. It checks the regular
file/no-follow boundary, an 8 MiB archive limit, a 2 MiB member limit, a 4 MiB
total uncompressed limit, exact member names, ZIP symlink/path safety, manifest
digests, Workflow DSL validation, and secret-like values. Invalid bundles
return a stable redacted report and a non-zero exit code.

Publish a verified bundle into one explicit local control plane:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-publish \
  /tmp/approval-flow.s2w \
  --state-dir /tmp/skill2workflow-control \
  --storage sqlite
```

`bundle-publish` performs the same complete in-memory verification first, then
passes the validated Workflow DSL to the normal immutable publication path.
It never runs the workflow, resolves credentials, calls a connector, or
overwrites a different published artifact. A repeated identical publication
is idempotent under the existing control-plane contract; a different document
for the same workflow/version is rejected as an immutable-artifact conflict.

Review two bundles before publication:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-diff \
  /tmp/approval-flow-old.s2w \
  /tmp/approval-flow-new.s2w
```

`bundle-diff` verifies both bundles before comparing them with the same
value-free structural semantics as the published `workflow-diff` command. It
reports only workflow identity, versions, digests, changed sections, and node
or edge IDs. Titles, descriptions, connector requests, trigger inputs, and
credentials never enter the report. Different workflow IDs fail closed rather
than producing a misleading comparison.

Check a received bundle and optional trigger input without creating state or
calling a connector:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-preflight \
  /tmp/approval-flow.s2w \
  --input /tmp/approval-flow-input.json \
  --format text
```

`bundle-preflight` verifies the bundle in memory and reuses the fixed trigger
input, input-schema, and connector-mapping admission contract. Its report is
side-effect-free and value-free: it reports input keys/counts and mapping
status, never input values, credentials, connector calls, or run state. A
blocked report exits non-zero so it can gate a later `bundle-run` step.

Run a verified bundle through the normal local executor without publishing it:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/approval-flow.s2w \
  --state-dir /tmp/skill2workflow-bundle-run \
  --storage sqlite
```

`bundle-run` verifies the bundle before creating run state, then uses the same
executor, storage, retry, timeout, and credential-file boundaries as `run`.
It always requires the same `bundle-preflight` admission report to be ready.
When the report contains connector nodes, the operator must also pass the
explicit `--allow-side-effects` switch; without it the command exits before
creating state, resolving credentials, or making a network call. With
`--input`, the bounded input is stored under `context.input`. An authorized
run may execute explicitly requested connector side effects, but it does not
create a published version, promote an alias, or introduce a second execution
authority. Invalid bundles fail before the state directory is initialized.

Automation that needs a stable refusal contract can add `--format json`:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/connector-flow.s2w \
  --format json \
  --state-dir /tmp/skill2workflow-bundle-run
```

When connector side effects are present and consent is missing, the command
returns exit code 1 and emits the value-free
`skill2workflow-workflow-bundle-run-0.1.0` report. It includes the workflow
identity, Bundle SHA-256, stable reason code, side-effecting node count, and
the `side_effect_consent_required` reason, plus false safety flags for state
creation, credential resolution, connector calls,
and raw values. The default invocation keeps the existing human-readable
stderr message.

For a successful run, add `--summary` when a script or handoff needs only
bounded status and provenance rather than the complete local run state:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/approval-flow.s2w \
  --summary \
  --state-dir /tmp/skill2workflow-bundle-run
```

The value-free `skill2workflow-workflow-bundle-summary-0.1.0` output contains
the run identity, status counters, and the three `context.bundle_run` evidence
fields. It omits Workflow DSL, trigger input, node-result payloads, connector
responses, and credentials. Without `--summary`, the existing complete local
run-state output remains available for debugging.

Every successful `bundle-run` also stores a compact `context.bundle_run`
metadata object with `bundle_verified`, `side_effects_authorized`, and the
lowercase SHA-256 digest of the exact verified archive in `bundle_sha256`.
This helps an operator distinguish an explicitly authorized local execution
from a side-effect guard rejection and identify the exact input artifact
without recording bundle values, paths, credentials, or provider payloads. The
digest is computed during the same bounded read that supplies the executable
Workflow DSL, avoiding a second path read. It is run-state evidence, not a
signed approval record or a replacement for the control-plane audit boundary.

The successful bundle verification report contains only workflow identity,
status, byte counts, archive/workflow SHA-256 digests, member count, and fixed
error fields. The
preflight report likewise exposes only bounded structural metadata and input
keys/counts. Neither report echoes workflow descriptions, trigger input values,
connector URLs, request bodies, credential values, or provider responses.

## Reproducibility and trust boundary

Bundle member order, JSON key order, ZIP timestamps, and file permissions are
fixed, so the same validated Workflow DSL produces identical bundle bytes.
The SHA-256 digest binds `workflow.json` to the manifest; it is an integrity
check, not a signature or a publisher identity proof. Reviewers should verify
the bundle through a trusted channel and still inspect the Workflow DSL before
publication.

The format intentionally excludes source `SKILL.md`, arbitrary attachments,
connector package code, and runtime state. Keep those materials in the normal
source-control or release process rather than smuggling them into a workflow
artifact.

The manifest contract is versioned at
[`schemas/workflow-bundle-0.1.0.schema.json`](../schemas/workflow-bundle-0.1.0.schema.json).
The value-free diff contract is versioned at
[`schemas/workflow-bundle-diff-0.1.0.schema.json`](../schemas/workflow-bundle-diff-0.1.0.schema.json).
The structured side-effect refusal contract is versioned at
[`schemas/workflow-bundle-run-0.1.0.schema.json`](../schemas/workflow-bundle-run-0.1.0.schema.json).
The value-free successful-run summary contract is versioned at
[`schemas/workflow-bundle-summary-0.1.0.schema.json`](../schemas/workflow-bundle-summary-0.1.0.schema.json).
The capability is local-only in this loop; it does not add remote upload,
marketplace discovery, hosted signing, or migration of published service state.
