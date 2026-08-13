# Local Workflow Inventory

Loop 127 adds an optional bounded view for operators inspecting published
workflow versions on the self-hosted host. The complete list remains available
for local evaluation when `--limit` is omitted.

## Bounded Command

```bash
skill2workflow workflows \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite \
  --limit 100
```

From a source checkout, prefix the command with
`PYTHONPATH=src python3 -m skill2workflow.cli`.

`--limit` accepts `1` through `100`. The result uses the existing
`skill2workflow-workflow-inventory-0.1.0` contract from
[`schemas/workflow-inventory-0.1.0.schema.json`](../schemas/workflow-inventory-0.1.0.schema.json).
It contains only workflow id, version, lifecycle status, aliases, and checksum,
plus aggregate counts and a truncation window. Workflow titles, descriptions,
nodes, edges, connector requests, trigger inputs, credentials, and artifact
contents are not returned.

The newest versions by publication time are retained. A complete-list request
without `--limit` keeps the historical raw local output for compatibility and
local evaluation; it is not the bounded production operator projection.

## Safety Boundary

This command is read-only. It does not acquire the scheduler lease, mutate the
registry, read workflow artifacts for content, promote aliases, trigger runs,
or deprecate versions. Operators should use `workflow-diff` for a structural
review and the CAS-protected `promote` command for a subsequent alias change.

The fixed schema and redaction boundary are shared with the authenticated
`service-workflows` projection, but this local command does not add a network
route or change the remote service contract.

Focused verification:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_cli.CliTests.test_workflows_command_supports_bounded_redacted_inventory_window \
  tests.test_cli.CliTests.test_workflows_command_rejects_invalid_bounded_inventory_limit -v
```
