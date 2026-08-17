# Release Artifact Qualification

Loop 50 turns installability into release evidence. The qualification builds a
real wheel from the source tree, installs that wheel into a separate virtual
environment, and runs the installed product from a directory outside the
repository.

## Evidence Command

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```

The command creates two isolated environments:

- `build-venv` contains the packaging toolchain and builds exactly one
  `skill2workflow-*.whl` artifact;
- `venv` installs only that wheel with `--no-index --no-deps` and runs the
  installed console script.

Runtime checks execute under `PYTHONNOUSERSITE=1` with `PYTHONPATH` removed.
They run from `isolated/`, not from the checkout, and verify package metadata,
workflow validation, production-module imports, and help for the minimum
release command set: publish/run, service, recurring dispatch, backup/restore,
state upgrade, retention, cancellation, and operator snapshot export.
The installed command set also includes the protected `service-resume`,
`service-cancel`, redacted `service-show`, bounded `service-runs`, bounded
`service-run-page`, bounded
`service-audit-events`, bounded
`service-recurring-schedules`, bounded `service-recurring-dispatches`, bounded
`service-workflow-artifacts`, bounded `service-backup-readiness`, bounded
`service-backup-inventory`, bounded
`service-retention-readiness`, bounded
`service-operational-readiness`, bounded
`service-probe`, bounded `service-wait`, bounded `service-audit-integrity`, bounded
`service-runtime-info`, protected
`service-workflow-publish`, protected
`service-workflow-promote`, protected
`service-workflows`, protected
`service-workflow-diff`, protected
`service-workflow-deprecate`, protected
`service-trigger`, protected
`service-schedule-enable`, `service-schedule-disable`,
`service-recurring-schedule-add`, `service-recurring-schedule-update`,
`service-recurring-schedule-delete`, and
owner-only `service-support-bundle` operator
clients.

The installed command set also includes local `service-token-rotate`; package
qualification runs it against the generated bootstrap workspace and verifies
that the new token is usable while neither token value appears in command
output.

The qualification also starts a strict loopback fixture and makes the installed
`control-snapshot` command perform one authenticated live fetch. It verifies the
fixed endpoint, protected token-file path, bounded schema, empty standard output,
and owner-only `0600` artifact from outside the source checkout. It also runs
the installed `systemd-unit` command against a fixed-port copy of the secure
bootstrap configuration, checking the generated unit's permissions, journal
output directives, state-only write path, sandboxing, and secret redaction.

The wheel is also passed through `scripts/release_manifest.py`. The
qualification writes `release-artifact-manifest.json` under its work directory
and reports the archive SHA-256, member SHA-256 hashes, member count, and
manifest status. The manifest is a public, value-free integrity companion; see
[`release-artifact-manifest.md`](release-artifact-manifest.md) for the schema
and independent verification sequence.

The same qualified wheel is passed through `scripts/release_sbom.py`. The
qualification writes `release-artifact-sbom.json` with an SPDX 2.3 package,
one SHA-256 entry per wheel member, and `CONTAINS` relationships. Its document
comment binds the SBOM to the archive SHA-256, and the generator inherits the
manifest's fail-closed private-content and zero-runtime-dependency boundary;
see [`release-artifact-sbom.md`](release-artifact-sbom.md).

The release path also runs `scripts/reproducible_build.py`. It builds the
checkout twice with a fixed `SOURCE_DATE_EPOCH`, compares the wheel bytes and
release manifests, and writes `reproducible-build.json` as public evidence;
see [`reproducible-builds.md`](reproducible-builds.md) for the exact inputs and
review boundary.

Before installation, the qualification opens the wheel itself. It requires
the byte-for-byte official Apache-2.0 license under the single `dist-info`
directory, pinned by SHA-256, verifies the name, version, license expression,
and Python compatibility metadata, and allows only the `skill2workflow`
package plus its `dist-info` content. It rejects private or state artifacts
such as Pilot evidence, secret directories, SQLite databases, tokens, keys,
JSONL state, bytecode, and unexpected top-level trees.

The inspected METADATA also carries canonical Homepage, Documentation,
Repository, Issues, Changelog, and Security project URLs plus classifiers for
Python 3.9 through 3.14. The CI matrix proves the supported floor and current
stable endpoint; the classifiers make the same compatibility intent visible
to package-index users, while the extra links expose release history and the
private vulnerability-reporting policy directly from the package record.

An editable install remains useful for development, but it is not release
artifact evidence because imports may still resolve from the checkout.

## Release Preflight

`scripts/release_preflight.py` includes the wheel qualification in its default
verification commands. The release pull-request workflow watches the package
smoke, packaging tests, release tests, metadata, and release inputs so those
changes cannot bypass artifact verification.

The package metadata classifier is aligned with the documented Self-hosted
Beta maturity. The package version and Workflow DSL compatibility line remain
unchanged until a separately approved release is prepared.

## Boundary

This qualification does not upload a package, create a tag, publish a GitHub
Release, sign an artifact, attest a source commit, compare independent
builders, or certify every supported operating system and Python version. The
manifest, SPDX SBOM, and fixed-epoch reproducibility evidence are public
integrity/inventory/review companions, not signatures, trusted key
attestations, or registry publication.
