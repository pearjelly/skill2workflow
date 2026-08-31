# Audit Evidence Export Design

## Goal

Add one local, SQLite-only operator command that writes a bounded, redacted
audit-evidence file for incident handoff. It must compose the existing audit
chain verifier with the existing safe audit-page projection; it must not
reimplement either projection or expose raw audit payloads.

## Proposed command

```bash
skill2workflow audit-evidence \
  --state-dir /var/lib/skill2workflow \
  --output /var/lib/skill2workflow-evidence/audit-window.json \
  --max-items 100
```

Optional exact filters match the existing remote audit page:
`--workflow-id`, `--workflow-version`, `--run-id`, and `--event-type`.

## Contract

- SQLite storage is mandatory; JSON storage fails closed before creating output.
- The command verifies the local audit chain first. Only `status: valid` may
  produce evidence; legacy or invalid chains produce no output file.
- The exported event page is produced by
  `build_audit_event_page_from_control`, with the existing 1–100 item bound.
- Output includes the redacted page plus the existing value-free integrity
  report. It records whether the page is truncated and its opaque next cursor;
  it never claims to be a complete audit-history export.
- Output is a newly created owner-only regular file. Existing paths, symlinks,
  non-regular targets, and unsafe parents are refused. Write to a private
  sibling temporary file, fsync, then rename.
- The result printed to stdout is compact: output path, event count, truncated
  flag, and integrity head digest only. It contains no event values.

## Exclusions

This does not add remote audit download, full-history streaming export,
signature or encryption, audit-chain repair, provider reconciliation, RBAC,
retention policy, or a claim of compliance certification.

## Acceptance evidence

1. A valid SQLite state creates one owner-only evidence file containing only
   allowlisted page fields and no raw connector or trigger values.
2. A tampered audit chain, JSON storage, existing output, or symlink output
   refuses before output creation.
3. Filters, 1–100 bounds, and truncation/opaque cursor match the current audit
   page contract.
4. CLI, installed-wheel smoke, docs, secret hygiene, and full regression pass.
