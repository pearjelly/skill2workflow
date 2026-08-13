# Loop 65: SQLite Audit Integrity

**Status:** Complete

## Goal

Make durable SQLite audit evidence independently verifiable after normal
operation, verified backup/restore, and copy-on-write retention.

## Contract

- New SQLite `audit_events` rows carry `prev_digest` and `digest` fields.
- `digest` is SHA-256 over `sha256-chain-v1`, the sequence, the previous
  digest, and canonical event JSON.
- `audit-verify` returns a fixed, payload-free result and exits nonzero for an
  invalid or legacy-unsealed store.
- Opening the known legacy audit table adds the columns and seals existing
  valid rows; malformed JSON fails closed.
- Backups reject an invalid current chain; retention rebuilds the retained
  chain after intentional deletion.

## Exclusions

No remote audit service, digital signature, external key management, immutable
storage, JSON/JSONL chain claim, or hosted compliance policy is introduced.

## Evidence

- Contract tests cover valid chains, payload tampering, legacy-column upgrade,
  compact CLI output, and backup/restore preservation.
- Retention tests prove the retained copy remains valid after deletion.
- Full regression, package smoke, schema parsing, compile, and secret-hygiene
  checks are required before publication.
