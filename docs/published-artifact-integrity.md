# Published Artifact Integrity

Loop 70 adds a runtime integrity guard for every published Workflow DSL
artifact. The control-plane registry stores a canonical JSON checksum at
publication time. Before a published version is inspected, promoted, run, or
triggered, the runtime reloads the artifact and compares its canonical checksum
with the registry value.

## Failure Boundary

If the artifact is missing, unreadable, malformed, missing its registry
checksum, or no longer matches that checksum, the operation fails closed with a
fixed error that identifies only `workflow_id@version`:

```text
published workflow artifact unavailable: <workflow_id>@<version>
published workflow artifact checksum unavailable: <workflow_id>@<version>
published workflow artifact checksum mismatch: <workflow_id>@<version>
```

The runtime does not expose the artifact path, file contents, or registry
payload in the error. A failed integrity check happens before input validation,
SQLite trigger-idempotency claims, run creation, audit emission, or alias
mutation. A corrupted release therefore cannot become reachable through a
stable alias or start a new run.

The checksum covers the parsed JSON value using the same canonical encoding
used during publication. Reformatting whitespace alone does not change the
workflow meaning; changing any JSON value does.

## Operator Response

Treat an integrity failure as a deployment or state incident:

1. Stop traffic to the service and preserve the state directory for review.
2. Do not edit the workflow artifact or registry checksum by hand.
3. Verify the latest offline backup with `skill2workflow backup-verify`.
4. Restore into a new directory, or republish the intended content under a new
   immutable version after the incident is understood.
5. Run the service readiness check and a controlled trigger before returning
   traffic.

The guard detects local accidental or untrusted modification. It is not a
digital signature, remote attestation, or protection against an operator who
can rewrite both the artifact and its control database. Keep the state
directory owner-only and use the verified backup/restore contract in
[`backup-restore.md`](backup-restore.md).

## Compatibility

Published records created by the current runtime always contain a checksum.
Records without one are rejected at read time rather than executed
unverified. Existing unversioned SQLite state must first pass the documented
state upgrade; the upgrade preserves the existing registry and artifact
checksums and does not synthesize trust for a missing value.
