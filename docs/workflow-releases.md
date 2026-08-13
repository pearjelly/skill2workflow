# Reviewable Workflow Releases

Loop 71 adds a bounded review step between publishing an immutable workflow
version and moving a stable trigger alias. The control plane can compare two
published versions without copying their titles, instructions, connector
requests, input values, or other workflow content into the diff output.

## Structural Diff

Run the diff against exact published versions:

```bash
skill2workflow workflow-diff workflow_approval_flow \
  --from-version 0.1.0 \
  --to-version 0.2.0 \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite
```

From a source checkout, prefix the command with
`PYTHONPATH=src python3 -m skill2workflow.cli`.

The output contract is
`skill2workflow-workflow-diff-0.1.0`, published at
[`schemas/workflow-diff-0.1.0.schema.json`](../schemas/workflow-diff-0.1.0.schema.json).
It contains the two immutable version records (status, checksum, and aliases),
the changed sections, and added/removed/changed node and edge identifiers. It
contains no node titles, descriptions, connector URLs, request bodies,
credentials, trigger inputs, or arbitrary field values. Both artifacts are
integrity-checked before the diff is produced.

`changed: false` is a valid result when the parsed Workflow DSL values are
equivalent. Version numbers and publication metadata are intentionally not
counted as workflow-content changes.

## Compare-And-Swap Promotion

When multiple operators may be preparing a release, protect the alias move
with the version observed during review:

```bash
skill2workflow promote workflow_approval_flow \
  --version 0.2.0 \
  --alias production \
  --expected-current-version 0.1.0 \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite
```

The promotion succeeds only when the alias still points to exactly the
expected published version. A missing, ambiguous, or different current target
returns the fixed error:

```text
workflow alias precondition failed: <workflow_id>@<alias>
```

The failed operation does not mutate aliases or append a promotion audit event.
Omitting `--expected-current-version` preserves the original explicit
single-operator promotion behavior. The target artifact is still integrity
checked before any alias metadata changes.

For SQLite-backed self-hosted state, the compare-and-swap check, alias updates,
and `workflow_promoted` audit row are committed by one `BEGIN IMMEDIATE`
transaction. If two operators review the same current version concurrently,
exactly one matching promotion can commit; the other observes the new alias
target and receives the fixed precondition error. A failed transaction leaves
both the alias registry and the audit chain unchanged. This is the production
concurrency contract; JSON storage remains the dependency-light local
evaluation mode and does not provide cross-process transaction coordination.

## Boundary

This is an operator review aid and a SQLite-backed local optimistic-concurrency
guard. It is not a policy engine, approval workflow, semantic business-risk
analyzer, automatic canary, health-based rollout, rollback controller,
signature, or multi-tenant release service. Operators remain responsible for
reviewing the published diff and choosing the target version.
