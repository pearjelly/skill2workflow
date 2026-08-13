# Plan: Targeted Remote Run Audit Inspection

## Goal

Let an authenticated self-hosted operator inspect one known run when the
bounded global audit-consistency report has reached its 256-run window.

## Scope

- extend the existing read-only audit route with a fixed `run_<id>` path;
- reuse the run identifier safety grammar in the remote client and CLI;
- preserve the existing `skill2workflow-run-audit-report-0.1.0` schema and
  redaction, with a one-run untruncated projection;
- return fixed errors for malformed or unknown targets without path disclosure;
- keep authentication, readiness independence, response bounds, and zero-write
  behavior unchanged.

## Verification

- service coverage proves targeted selection beyond the global window;
- client coverage proves exact path construction and pre-network rejection;
- CLI coverage proves the installed `--run-id` contract;
- full unittest, package, service-boundary, secret-hygiene, compile, and diff
  checks pass before commit.
