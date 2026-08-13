# Grafana Dashboard

The repository includes an importable Grafana dashboard at
[`examples/observability/grafana-dashboard.json`](../examples/observability/grafana-dashboard.json).
It is designed for the fixed Prometheus metrics and the same single-tenant
operator boundary as the alert starter pack in
[`prometheus-alerts.md`](prometheus-alerts.md).

## Import

1. Configure the Prometheus data source that scrapes the authenticated
   `/metrics` endpoint through the external TLS/operator boundary.
2. Import `grafana-dashboard.json` in Grafana and select the Prometheus data
   source when prompted.
3. Review the panel time range and notification/access policy before sharing
   the dashboard.

The dashboard has no hard-coded host, port, tenant, workflow, run, schedule,
credential, or provider values. Its only import variable is the Prometheus data
source. It uses the fixed metric labels `status` and `status_class` only.

## Panels

- service readiness and scheduler-lease ownership;
- current in-flight business requests against the fixed 16-slot budget;
- durable uncertain dispatch count;
- HTTP response rate by fixed response class;
- run attention states (`running`, `waiting`, `failed`, `interrupted`, and
  `cancelled`);
- dispatch attention states (`claimed`, `failed`, and `uncertain`); and
- process uptime.

The panels are read-only views. A red or elevated panel is a cue to follow the
operator guides and the alert runbook; it never authorizes blind replay,
cancellation, schedule mutation, or a change to service lifecycle state.

## Verification

The repository smoke validates the JSON shape, fixed panel count, Prometheus
data-source input, metric vocabulary, label vocabulary, and absence of
credential-like or workflow-value markers:

```bash
python3 scripts/observability_dashboard_smoke.py
```

Grafana remains the authority for version-specific import compatibility. Test
the import on the target Grafana version before using it as an operational
source of truth.
