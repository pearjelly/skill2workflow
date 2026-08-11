# Controlled Pilot Deferral Review

## Scope And Decision

This review records the Loop 40 controlled live Pilot after the partner and
operator both confirmed `defer`. It is an operational boundary record, not
completion evidence and not authorization for another live request.

The original private workspace is closed. There is no retry, replacement, or
additional live decision under that workspace. Its owner-only history remains
authoritative; no raw task values, identifiers, credentials, request bodies,
response bodies, or provider diagnostics are committed here.

## Supported Facts

- The scoped Lark task connector previously completed one separately approved
  live `create_task` validation; the compact redacted record is in
  [`lark-live-connector-validation.md`](lark-live-connector-validation.md).
- The controlled Pilot recorded one approved live completion, a human
  rejection with no connector invocation, and passing disabled-live and
  rollback exercises.
- A later explicitly approved controlled attempt returned the normalized
  status `validation_failed`. It did not reach the five approved live runs
  across five `Asia/Shanghai` calendar days required by Loop 40.
- The connector intentionally retained no raw provider message. Therefore the
  review cannot attribute that `validation_failed` result to a specific
  provider field, permission, task member, deadline, or task value.

The current local `preflight` reconstructs the same fixed Task v2 payload
without credentials or network access. It verifies the locally knowable
request shape: a non-empty summary, optional description, open-id assignee
member, timezone-aware millisecond deadline, and deterministic client token.
This gives local contract evidence only; it does not prove future provider
acceptance and does not change the historical result.

## Re-entry Gate For A Separately Authorized Pilot

A future Pilot may be considered only after fresh partner and operator
authorization. It must use a new private work directory, a new valid Charter,
new owner-only case files, and the no-network `preflight` before each `start`.
Every real create remains a separate inspected human approval with the live
switch and Vault injection present only for that one command.

The replacement engagement must independently complete five approved live
runs across five distinct `Asia/Shanghai` dates, use at least two opaque case
ids, contain a human rejection, pass the failure and rollback exercises, and
pass fixed verification before it can be finalized. It cannot count or repair
the deferred workspace's history.

If an equivalent normalized failure occurs, stop the new Pilot, retain its
private facts, and obtain a new decision instead of widening the API action,
capturing raw provider content, or issuing a retry. Any request to broaden the
connector beyond the fixed domestic `create_task` boundary requires a separate
readiness review.

## Current Status

This original workspace remains deferred and closed. It is a historical
incident record, not evidence for another write. A separately authorized
Pilot subsequently satisfied Loop 40 under a new workspace and authorization
boundary; its finalized redacted evidence is in
[`docs/pilot-evidence/loop-40/`](pilot-evidence/loop-40/). Repository tests
and dry-runs remain insufficient on their own for any future paid engagement.
