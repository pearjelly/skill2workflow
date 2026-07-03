# Release Process

This project keeps release creation manual until the release automation has been exercised on a patch release. The preflight command is read-only: it checks release inputs and verification evidence, but it does not create tags, publish GitHub Releases, upload packages, or write repository state.

## Maintainer Preflight

Before opening a release PR for a future patch release, update all release inputs in the branch:

- `pyproject.toml`
- `src/skill2workflow/__init__.py`
- `docs/releases/v<version>.md`

Then run the full local preflight from a clean branch:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py --version 0.1.1 --notes docs/releases/v0.1.1.md --dry-run
```

The command checks:

- package version in `pyproject.toml`
- module version in `src/skill2workflow/__init__.py`
- release notes filename and content
- clean working tree
- local and `origin` tag availability
- full unit suite
- Python module compilation

The command fails before any GitHub operation when release notes, package version, module version, or tag inputs disagree.

## Release PR Evidence

Release PRs should include the preflight output and any extra release-specific checks. At minimum, include:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py --version <version> --notes docs/releases/v<version>.md --dry-run
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
git diff --check
```

If the preflight command already ran the unit suite and compile check, it is acceptable to cite that output once instead of duplicating the logs.

## CI Dry-Run

`.github/workflows/release-preflight.yml` runs a pull-request dry-run for release-related files. It reads the package version from `pyproject.toml`, derives `docs/releases/v<version>.md`, and runs:

```bash
PYTHONPATH=src python scripts/release_preflight.py --version <version> --notes docs/releases/v<version>.md --dry-run --skip-git
```

CI skips git cleanliness and tag availability because pull-request checkouts are not the release source of truth and the current released tag may already exist. Local maintainer preflight must not skip git checks before a real release.

## Manual Fallback

The `v0.1.0` release was created manually from verified `main`. Keep this path available until a patch release proves the automation:

```bash
git switch main
git pull --ff-only
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/approval-flow.workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/http-connector.workflow.json --format json
git tag -a v<version> -m "skill2workflow v<version>"
git push origin v<version>
gh release create v<version> --title "skill2workflow v<version>" --notes-file docs/releases/v<version>.md
```

Use the manual fallback only after the release PR has merged and `main` is clean.

## Current Boundary

Release automation is a guardrail, not a publisher. It intentionally does not:

- auto-publish GitHub Releases from pushed tags
- upload packages to a registry
- sign release artifacts
- manage credentials or release approvals
