# Reproducible Release Builds

Loop 150 adds a small, dependency-free proof for the release wheel. It builds
the current checkout twice in a fresh virtual environment, with the same fixed
build inputs, and requires both the wheel bytes and the release manifest to be
identical.

## Evidence command

```bash
python3 scripts/reproducible_build.py \
  --work-dir /tmp/skill2workflow-reproducible-build
```

The command creates an isolated build environment, installs the minimum
packaging toolchain, and invokes `pip wheel --no-deps --no-build-isolation`
twice. Each build receives the same value-free environment:

- `SOURCE_DATE_EPOCH=946684800` (2000-01-01T00:00:00Z by default)
- `PYTHONHASHSEED=0`
- `TZ=UTC`
- `LC_ALL=C` and `LANG=C`

Use `--source-date-epoch` to review another Unix timestamp between 1970 and
2100. The work directory must be outside the repository; it is reset by
default so stale wheels cannot be mistaken for fresh evidence.

## Public evidence

On success the command writes `reproducible-build.json` with schema
`skill2workflow-reproducible-build-0.1.0`. It contains the fixed source date,
the wheel filename, archive SHA-256, member count, the two-build comparison,
and the build environment. It never contains source contents, credentials,
workflow input, or private state. The file is written atomically with mode
`0644`.

The evidence is a review companion, not a signature. A reviewer can rerun the
command, compare the recorded archive digest, and inspect the corresponding
`release-artifact-manifest.json` and SPDX SBOM from package qualification.

## Release integration

The default release preflight runs this check after the isolated package smoke.
The CI `artifact-gates` job repeats it on Python 3.14. Contributors can run the
same command locally before opening a release or packaging change.

## Boundary

This proves byte equality for two builds of one checkout under one fixed
toolchain and environment. It does not sign artifacts, attest a source commit,
verify every operating system or Python implementation, compare independent
builders, upload to a registry, or claim hosted supply-chain security. Those
controls remain separate release decisions.
