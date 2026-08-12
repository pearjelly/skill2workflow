# Governance

`skill2workflow` is currently a maintainer-led open-source project at
Self-hosted Beta maturity. This document describes how technical, product,
security, and release decisions are made without implying a foundation,
committee, service-level agreement, or commercial support organization.

## Current Maintainer

The project currently has a single active maintainer:

- [@pearjelly](https://github.com/pearjelly)

The maintainer owns repository administration, review and merge decisions,
release approval, private security coordination, Roadmap stewardship, and the
documented product boundary. Contributors do not need maintainer status to
open issues, propose designs, review public changes, or submit pull requests.

## Decision Process

Routine changes are proposed through a public pull request with tests,
compatibility notes, and security/privacy evidence appropriate to the change.
The Workflow DSL remains the execution truth source. Changes to parser,
compiler, executor, storage, connector, service, or release behavior should
follow the repository's test-first and closed-loop rules.

Substantial product direction changes require an explicit Roadmap decision and
a reviewable design or plan before implementation. Choosing a version and release
is a separate maintainer decision; completing a Roadmap loop or adding an
`Unreleased` changelog entry does not publish a version.

Suspected vulnerabilities never use the public decision path. Follow
`SECURITY.md` for private security reporting and coordinated disclosure.
Conduct and moderation reports follow `CODE_OF_CONDUCT.md`.

When consensus is not immediate, the maintainer records the decision and its
evidence in the pull request, Roadmap, design document, or release notes. The
project may defer a proposal when evidence is incomplete or the work exceeds
the current single-tenant, dependency-light boundary.

## Review And Merge

All contributors, including the maintainer, should use pull requests for
substantive changes. CI, focused regression evidence, compatibility review,
and clean secret-hygiene results are required according to
`CONTRIBUTING.md`. With a single active maintainer, two-person approval cannot
be promised; critical security, state, migration, release, and license changes
must compensate with explicit tests, reproducible commands, and documented
rollback or failure boundaries.

CODEOWNERS is review routing, not authorization, branch protection, or a
security boundary. Repository permissions and GitHub protection settings
remain authoritative for who may merge or administer the project.

## Maintainer Changes

Future maintainers should demonstrate sustained, constructive contributions,
sound judgment around compatibility and private data, and willingness to
uphold the Roadmap, security policy, and Code of Conduct. The existing
maintainer may grant or remove repository roles and should record material
maintainer changes in this file through a public pull request when safe.

If the current maintainer is unavailable, contributors may continue proposing
and reviewing changes, but they must not claim release authority, security
custody, or project ownership without an actual repository permission change.

## Scope

This governance model covers the public `skill2workflow` repository. Forks,
private deployments, partner operations, hosted services, and commercial
agreements remain under their respective owners and are not governed by this
document.
