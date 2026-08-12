# Support

`skill2workflow` is an open-source Self-hosted Beta for one team's
single-tenant runtime. Community support is best-effort; there is no hosted
service, paid incident desk, or service-level agreement.

## Where To Ask

- Reproducible defect: use the GitHub bug report form.
- Focused product proposal: use the feature request form.
- Sanitized real-world workflow: use the workflow example form.
- Security vulnerability: follow [the security policy](SECURITY.md) and report
  privately.
- Contribution question: read [the contributor guide](CONTRIBUTING.md),
  [the Roadmap](ROADMAP.md), and the relevant operator guide before opening an
  issue.

Include the package version or commit, Python version, operating system,
storage mode, expected result, actual result, and a minimal reproduction. Remove
credentials, tokens, customer data, private workflow input, provider payloads,
and local secret paths.

## Operational Boundary

No emergency support is provided. Do not rely on a public issue for an outage,
active compromise, regulated incident, data-recovery deadline, or provider-side
reconciliation. Operators remain responsible for process supervision, external
TLS, host security, credential management, backups, retention decisions, and
reconciling interrupted external side effects.

The supported production direction and explicit exclusions are maintained in
[the Roadmap](ROADMAP.md). A request outside that boundary is welcome as
product evidence, but it is not an implicit support commitment.
