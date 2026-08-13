# Release Artifact Manifest

Loop 113 adds a dependency-free provenance manifest for the distributed
`skill2workflow` wheel. The manifest is a public companion file that lets a
user verify the downloaded archive and inspect its exact member set without
installing the package or trusting a source checkout.

## Generate

The package qualification generates the manifest automatically under its
work directory:

```bash
python3 scripts/package_smoke.py \
  --work-dir /tmp/skill2workflow-package-smoke
```

For an already-built wheel, generate one directly:

```bash
python3 scripts/release_manifest.py \
  --wheel dist/skill2workflow-0.1.1-py3-none-any.whl \
  --output dist/skill2workflow-0.1.1-py3-none-any.manifest.json
```

The writer publishes the JSON file atomically and uses a public `0644` mode.
It never embeds absolute paths, source contents, credentials, workflow
payloads, or environment values.

## Contract

The manifest uses schema
`skill2workflow-release-artifact-manifest-0.1.0` and contains:

- the wheel basename, byte length, and SHA-256 digest;
- the fixed distribution name/version, Python requirement, license expression,
  runtime dependency list, and wheel tags; and
- a lexicographically sorted list of every non-directory wheel member with its
  byte length and SHA-256 digest.

The generator rejects traversal or duplicate member names, symlinks and
private/state-like paths, unexpected top-level trees, mismatched `dist-info`
identity, and runtime dependencies outside the package's zero-dependency
contract.

## Verification boundary

A user can hash the downloaded wheel with any standard SHA-256 tool and compare
it to `artifact.sha256`, then inspect or independently hash the listed members.
The manifest is integrity evidence, not a digital signature, trusted key
attestation, SBOM, reproducible-build proof, or package-registry publication.
Those require a separately authorized release and supply-chain process.

The focused repository checks are:

```bash
PYTHONPATH=src python3 -m unittest tests.test_release_manifest -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```
