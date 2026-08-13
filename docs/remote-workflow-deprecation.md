# Remote Workflow Deprecation

Loop 90 adds a narrow authenticated lifecycle action for operators that need to
retire one published Workflow DSL version through the installed service
boundary. It is deliberately smaller than publication and promotion: the
service changes only the registry status and stable-alias metadata already
owned by the SQLite control plane.

## Command

```bash
skill2workflow service-workflow-deprecate workflow_approval_flow \
  --version 0.1.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The token file is read locally and is never printed. The command validates both
path components before making a request. The service remains loopback-bound by
default; an external TLS/authentication boundary is required for deployment
behind a proxy (see [`security-boundary.md`](security-boundary.md)).

## Fixed HTTP contract

The client sends exactly one bounded JSON object to
`POST /api/v1/workflow-deprecations`:

```json
{
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0"
}
```

The route requires a ready service, the active scheduler lease, and a valid
Bearer token. The request is limited to the shared 1 MiB JSON body bound. A
successful response is exactly:

```json
{
  "schema_version": "skill2workflow-workflow-deprecation-0.1.0",
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0",
  "status": "deprecated",
  "checksum": "<64 lowercase hex characters>"
}
```

The response is capped at 16 KiB and contains no artifact path, Workflow DSL,
alias list, timestamp, credential, or request value. A missing version returns
`404`; malformed input returns the fixed `400` error. The installed client also
maps an upstream transport conflict to its fixed redacted `409` error shape.

## Semantics and safety boundary

Deprecation is an atomic SQLite registry mutation. It marks the selected
published version `deprecated`, removes any stable aliases from that version,
and appends one `workflow_deprecated` audit event. Repeating the same request is
idempotent: it returns the same redacted record without appending a duplicate
deprecation event. The immutable published artifact remains on disk so the
existing artifact-consistency and backup checks can still account for it.

This action does not publish a new version, promote an alias, delete an
artifact, trigger a run, cancel a run, or export Workflow content. Operators
must explicitly publish and promote a replacement before directing new traffic
to it. Existing in-flight executions are not rewritten by deprecation.

## Verification

The release qualification checks that the installed command is present. The
service integration drill covers denied and malformed requests, authenticated
deprecation, alias removal, redacted responses, idempotent replay, and exactly
one audit event. The complete suite is run with:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src \
  python3 -m unittest discover -s tests -q
```
