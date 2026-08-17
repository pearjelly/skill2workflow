# Documentation Guide

`skill2workflow` is a self-hosted, single-tenant Workflow DSL runtime. Start
with the shortest useful path, then choose the guide for the boundary you are
working on.

## Start here

- [README](../README.md) — product boundary and the fastest controlled journey
- [Quickstart](quickstart.md) — install, bootstrap, run, approve, and trigger
- [Installed UI](installed-ui.md) — serve the packaged editor and control-plane inspector
- [Authoring](authoring.md) — compile Skills, edit the graph, and write back DSL
- [Examples](examples.md) — scenario gallery and repeatable inspection commands
- [Workflow DSL contract](workflow-dsl-contract.md) — execution truth and schema
- [Workflow bundles](workflow-bundles.md) — deterministic shareable artifacts

## Operate one self-hosted instance

- [Service](service.md) — authenticated loopback service and route boundary
- [Service bootstrap](service-bootstrap.md) — secure first-use workspace
- [Service Doctor](service-doctor.md) — read-only readiness diagnosis
- [Systemd supervision](systemd-service.md) — manually reviewed Linux unit
- [Recurring scheduling](recurring-scheduling.md) — durable dispatch semantics
- [Human approval](human-approval.md) — remote approve/reject handoff
- [Remote trigger](remote-trigger.md) — protected workflow start

## Review, recover, and troubleshoot

- [Workflow explanation](workflow-explanation.md) — value-free execution plan
- [Workflow preflight](workflow-preflight.md) — input and HTTP mapping admission
- [Workflow releases](workflow-releases.md) — diff, publish, promote, deprecate
- [Run list](run-list.md) and [run detail](run-detail.md) — redacted diagnosis
- [Support bundle](support-bundle.md) — bounded incident handoff
- [Audit integrity](audit-integrity.md) and [audit consistency](run-audit-consistency.md)
- [Backup and restore](backup-restore.md)
- [Upgrade and migration](upgrade-migration.md)
- [Retention](data-retention.md) and [cancellation](cancellation.md)
- [Interrupted recovery](interrupted-recovery.md)
- [Observability](observability.md), [alerts](prometheus-alerts.md), and [Grafana](grafana-dashboard.md)

## Extend and contribute

- [Connectors](connectors.md) — manifest and execution boundary
- [External connector loading](external-connector-loading-boundary.md) — bounded local fixture source handoff
- [Credential boundary](credential-boundary.md) — handles, rotation, and redaction
- [Runtime policy](runtime-policy.md) — retry, timeout, and fallback semantics
- [Compatibility](workflow-dsl-compatibility.md) and [stability](stability.md)
- [Release process](release-process.md), [artifact qualification](release-artifact-qualification.md), and [reproducible builds](reproducible-builds.md)
- [Security boundary](security-boundary.md)

Workflow DSL is always the execution source of truth. LiteGraph, snapshots,
explanations, preflight reports, and bundles are bounded views or distribution
surfaces; none of them silently changes runtime semantics.
