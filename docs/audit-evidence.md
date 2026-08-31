# Bounded Local Audit Evidence Export

`audit-evidence` creates one new, owner-only JSON file for a reviewed audit
window. It is for controlled evidence handoff from a self-hosted SQLite
runtime; it is not a backup, an audit archive, a remote download API, a
signature, or a claim of complete historical export.

## Preconditions and command

Stop or otherwise coordinate writes when a stable point-in-time window is
required. The command verifies the complete local SQLite audit chain before it
reads the bounded page and writes nothing if that verification is not `valid`.
JSON/JSONL state is intentionally rejected.

```bash
skill2workflow audit-evidence \
  --state-dir /var/lib/skill2workflow \
  --output /var/lib/skill2workflow-evidence/audit-window.json \
  --max-items 100
```

Use exact optional filters to minimize the handoff:

```bash
skill2workflow audit-evidence \
  --state-dir /var/lib/skill2workflow \
  --output /var/lib/skill2workflow-evidence/run-window.json \
  --max-items 25 \
  --workflow-id workflow_approval_flow \
  --workflow-version 0.1.0 \
  --run-id run_... \
  --event-type connector_failed
```

`--max-items` is mandatory-bounded to 1 through 100. The file contains the
fixed `skill2workflow-audit-evidence-0.1.0` envelope, a value-free audit-chain
integrity result, and the existing redacted
`skill2workflow-audit-event-list-0.1.0` page. Its `window.total`,
`window.returned`, `window.truncated`, and opaque `window.next_cursor` disclose
that it is only one page. Operators must not describe a truncated page as a
complete audit history.

The process stdout is intentionally smaller still: output path, event count,
truncation flag, and chain head digest. It never prints audit event values.

## Sensitive-data and filesystem boundary

The page has the same allowlisted projection as the remote audit-event tail:
safe identifiers and lifecycle status may appear, but Workflow DSL, trigger
context, connector metadata/results, credential values, raw provider errors,
and arbitrary audit payload keys are excluded. Review the generated file before
sharing; redaction reduces exposure but does not transform operational IDs into
anonymous data.

The output must be a fresh path. The command rejects an existing regular file,
symbolic link, or non-regular target rather than overwriting it. It creates
missing parent directories as owner-only, rejects unsafe parent components, and
uses descriptor-anchored no-follow checks plus a private temporary file, fsync,
and atomic publish. Treat the resulting `0600` file as private business
evidence. Do not place it in the repository, issue tracker, or a shared public
directory.

An invalid chain, legacy JSON/JSONL state, unsupported local filesystem safety
primitives, malformed filters, or output failure leaves no export. The command
does not repair the audit chain, retry connectors, mutate state, acquire a
scheduler lease, upload evidence, sign/encrypt output, or reconcile provider
outcomes. Use the verified offline backup path for durable full-state retention.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_audit_evidence \
  tests.test_audit_evidence_cli -v
```
