# Workflow Version Promotion Aliases

**Status:** Complete

## Goal

Give operators a stable trigger target such as `production` while keeping
published Workflow DSL artifacts immutable. A release should be promotable
without editing every schedule, webhook integration, or runbook command.

## Design

- Store optional `aliases` metadata on the existing workflow registry record.
  JSON and SQLite stores already preserve the complete record JSON, so this is
  additive and requires no state-layout or database migration.
- Add `LocalControlPlane.promote_workflow(workflow_id, version, alias)`.
  Promotion accepts only a published version, removes the alias from sibling
  versions of that workflow, assigns it to the target, and appends a compact
  `workflow_promoted` audit event.
- Resolve exact versions first, then published aliases. Deprecation removes
  aliases and never silently redirects to another version.
- Add the `promote` CLI command with a safe default alias of `production`.
- Preserve idempotency across promotion: SQLite ledger scope uses the
  requested version text (including an alias), while execution and the compact
  response use the resolved immutable version. A retry after promotion
  therefore replays the first result; a new key executes the new target.

## Verification

- JSON and SQLite control-plane tests cover promotion, persistence, alias
  movement, exact-version precedence, validation, and deprecation cleanup.
- SQLite trigger tests cover alias resolution, new-version execution after a
  promotion, and replay without a duplicate run or lifecycle audit.
- CLI tests cover publishing two versions, promoting `production`, and
  triggering through the alias.
- Documentation tests and the full suite preserve the existing public
  contracts, redaction boundary, and state-layout compatibility.

## Explicit exclusions

This loop does not add health-based canaries, automatic rollback, traffic
splitting, multi-tenant aliases, hosted release orchestration, or exactly-once
provider effects. Alias assignment is an explicit operator action.
