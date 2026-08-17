# Release Artifact SPDX SBOM

Loop 149 adds a dependency-free Software Bill of Materials for the distributed
`skill2workflow` wheel. The package qualification derives the document from the
same value-free wheel manifest used for archive integrity, so the SBOM cannot
describe files that were not accepted by the release boundary.

## Generate

The package qualification writes `release-artifact-sbom.json` under its work
directory:

```bash
python3 scripts/package_smoke.py \
  --work-dir /tmp/skill2workflow-package-smoke
```

For an already-built wheel, generate one directly:

```bash
python3 scripts/release_sbom.py \
  --wheel dist/skill2workflow-0.1.1-py3-none-any.whl \
  --output dist/skill2workflow-0.1.1-py3-none-any.spdx.json
```

The writer publishes the JSON atomically with public `0644` permissions. The
document contains no source paths, file contents, credentials, workflow values,
or environment values.

## Contract

The output is SPDX JSON `SPDX-2.3` with schema marker
`skill2workflow-release-sbom-0.1.0`. It contains:

- one `skill2workflow` package with version, Apache-2.0 license expression,
  and a PyPI package URL;
- one file entry for every non-directory wheel member, with the member path and
  SHA-256 checksum; and
- `CONTAINS` relationships from the package to each file.

The document comment carries the wheel archive SHA-256, allowing the SBOM to be
paired with the release manifest and downloaded wheel. The generator inherits
the manifest boundary: traversal, duplicate names, symlinks, private/state
paths, unexpected top-level trees, mismatched metadata, and runtime
dependencies fail closed.

## Verification boundary

The SBOM is a public inventory and checksum companion, not a signature, key
attestation, reproducible-build proof, registry upload, or hosted vulnerability
scan. Release operators remain responsible for publishing it alongside the
wheel and for any separate signing or provenance process.

Focused checks:

```bash
PYTHONPATH=src python3 -m unittest tests.test_release_sbom tests.test_package_smoke -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```
