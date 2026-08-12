## Problem and outcome

Describe the user, operator, or contributor problem and the concrete outcome.
Keep the change scoped to the current approved delivery loop.

## Verification

List exact commands and results, including focused tests and any required real
process, package, recovery, or secret-hygiene smoke.

## Compatibility and migration

Describe Workflow DSL, CLI, state-layout, schema, package, or operator impact.
State "None" only after checking the documented compatibility surfaces.

## Security and privacy

Describe credential, authentication, filesystem, network, audit, retention,
and private-data impact. Do not include vulnerability details in a public PR;
follow `SECURITY.md` instead.

## Checklist

- [ ] Workflow DSL remains authoritative over visual and runtime state.
- [ ] Tests were added before parser, compiler, executor, storage, connector, or CLI behavior changed.
- [ ] Documentation, schemas, examples, and compatibility notes are aligned.
- [ ] No secrets, credentials, or customer data are included.
- [ ] `git diff --check` and the relevant verification commands pass.
