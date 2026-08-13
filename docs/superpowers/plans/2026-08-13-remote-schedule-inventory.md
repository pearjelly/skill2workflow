# Plan: Remote Recurring-Schedule Inventory

## Goal

Give a self-hosted operator enough remote visibility to diagnose durable
recurring scheduling without shell access or permission to change schedule
state.

## Scope

- add one authenticated, read-only `GET /api/v1/recurring-schedules` route;
- stream normalized definitions and retain at most 100 projected items with
  next-run and compact last-run metadata;
- exclude trigger input, idempotency prefixes, lease owners, credentials, and
  dispatch mutation;
- publish a versioned schema and the protected `service-recurring-schedules`
  CLI client with a 64 KiB response bound;
- keep the existing support-bundle 0.1.0 route matrix stable while exposing
  the new route in full telemetry.

## Verification

- dashboard coverage proves bounded selection and trigger-input redaction;
- service coverage proves authentication, readiness-independent reads, and no
  scheduler mutation;
- client/CLI coverage proves exact path, schema, origin, and response bounds;
- full unittest, package, service-boundary, secret-hygiene, compile, and diff
  checks pass before commit.
