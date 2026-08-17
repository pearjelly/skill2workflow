# Workflow Bundles

Workflow bundles provide a small, portable way to share and review one
Workflow DSL artifact. A bundle is a deterministic ZIP archive containing
exactly two files:

- `workflow.json`: the validated Workflow DSL document;
- `manifest.json`: the fixed `skill2workflow-workflow-bundle-0.1.0` manifest,
  including the workflow digest, size, status, and connector IDs.

The bundle is a distribution format, not a second execution authority. The
runtime still validates and executes Workflow DSL, and a bundle never contains
credentials, resolved connector values, run state, or audit history.

## Create and verify

Create a bundle from a local Workflow DSL file:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-create \
  examples/workflows/approval-flow.workflow.json \
  --output /tmp/approval-flow.s2w
```

Creation validates the workflow and runs the repository's secret-hygiene
scanner. Existing output is not overwritten unless `--force` is supplied;
replacement is assembled in a temporary sibling and committed atomically.

Verify a bundle before importing or reviewing it:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-verify \
  /tmp/approval-flow.s2w
```

Verification is read-only and does not extract files. It checks the regular
file/no-follow boundary, an 8 MiB archive limit, a 2 MiB member limit, a 4 MiB
total uncompressed limit, exact member names, ZIP symlink/path safety, manifest
digests, Workflow DSL validation, and secret-like values. Invalid bundles
return a stable redacted report and a non-zero exit code.

The successful report contains only workflow identity, status, byte counts,
digests, member count, and fixed error fields. It does not echo workflow
descriptions, trigger inputs, connector URLs, request bodies, credential
values, or provider responses.

## Reproducibility and trust boundary

Bundle member order, JSON key order, ZIP timestamps, and file permissions are
fixed, so the same validated Workflow DSL produces identical bundle bytes.
The SHA-256 digest binds `workflow.json` to the manifest; it is an integrity
check, not a signature or a publisher identity proof. Reviewers should verify
the bundle through a trusted channel and still inspect the Workflow DSL before
publication.

The format intentionally excludes source `SKILL.md`, arbitrary attachments,
connector package code, and runtime state. Keep those materials in the normal
source-control or release process rather than smuggling them into a workflow
artifact.

The manifest contract is versioned at
[`schemas/workflow-bundle-0.1.0.schema.json`](../schemas/workflow-bundle-0.1.0.schema.json).
The capability is local-only in this loop; it does not add remote upload,
automatic installation, marketplace discovery, hosted signing, or migration
of published service state.
