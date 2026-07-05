# Stability Boundaries

`skill2workflow` is pre-alpha, but some surfaces are already stable enough for contributors and early adopters to build against. This document separates stable contracts from experimental internals.

## Stable For 0.1.x

These surfaces should remain compatible during the `0.1.x` line:

- Workflow DSL `0.1.0` top-level shape
- `schemas/workflow.schema.json`
- Structured validation error keys: `code`, `message`, `path`, `severity`
- CLI command names documented in `README.md` and `HARNESS.md`
- Example workflow fixture validity under `examples/workflows/`
- Published workflow artifact immutability
- JSON storage as the dependency-light default
- SQLite storage as an opt-in local persistence mode
- Built-in connector runtime boundaries documented in `docs/connectors.md`
- Credential placeholder and fixture hygiene boundary documented in `docs/credential-boundary.md`
- Local credential handle boundary documented in `docs/credential-boundary.md`
- Local trigger command and envelope documented in `docs/triggers.md`
- Local trigger run-context shape documented in `docs/triggers.md`
- Local webhook route and response shape documented in `docs/triggers.md`

## Experimental

These surfaces may change while the project learns from real workflows:

- Parser heuristics for arbitrary `SKILL.md` formats
- Skill IR shape
- Compiler defaults for new node types
- LiteGraph node layout and web editor UI
- Visual write-back allowlist beyond the documented fields
- Connector manifest details beyond built-in `manual` and `http`
- HTTP connector request metadata shape
- Advanced credential provider configuration beyond local static files
- Advanced retry behavior beyond documented connector-node retry execution
- Enterprise credential storage, secret redaction, and IAM
- Advanced trigger input mapping, templating, and connector request interpolation
- Hosted webhook ingress, callback verification, queues, and schedulers
- Local control-plane storage file layout
- Executor event taxonomy beyond documented audit examples
- Future UI/API boundaries

## Extension Rules

When extending stable surfaces:

- Preserve old readers where possible.
- Add structured validation coverage.
- Update schema and docs in the same PR.
- Keep examples runnable from a fresh checkout.
- Keep Workflow DSL authoritative over visual graph state.

When changing experimental surfaces:

- Keep the change scoped to one closed loop.
- Document migration notes if examples or contributor workflows are affected.
- Prefer additive changes over rewrites.

## Dependency Policy

Runtime code currently uses the Python standard library. New runtime dependencies should be added only when they directly support a spec-backed capability and the PR explains why standard-library code is insufficient.

Development-only tools may be introduced later, but the fresh-checkout path should remain simple.
