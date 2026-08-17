# External Connector Manifest Metadata Policy

## Goal

Keep the Loop 203 durable projection value-free while allowing a reviewed
external connector to retain a small connector-specific vocabulary. Hardcoding
every future provider's safe status or presence fields in the executor would
make the open-source extension boundary unusable; accepting arbitrary manifest
field definitions would turn the manifest into a persistence escape hatch.

## Contract

An external connector may add `audit_contract.durable_metadata` with exactly
these optional sections:

- `string_enums`: a mapping of field names to 1-32 finite identifier strings;
- `booleans`: a list of field names whose values must be JSON booleans;
- `lists`: a list of field names whose values are projected as sorted,
  deduplicated identifier names.

There are at most 32 fields in each section, field names are unique across all
sections, and names/values are bounded to 128 UTF-8 bytes with a restricted
identifier alphabet. Unknown sections, malformed declarations, duplicate
names, invalid enum values, nested objects, and arbitrary strings fail closed
or are dropped. The existing fixed vocabulary remains the default, and the
`input_mapping` and `credentials` summaries retain their fixed contracts.

## Safety boundary

Manifest validation occurs before explicit external fixture registration. The
policy only expands the set of values that the durable executor may retain; it
does not change the 1 MiB normalized result bound, imported-Python loading
boundary, direct runtime result contract, credential resolution boundary, or
exactly-once claims.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_manifest_declared_metadata_policy_is_bounded_and_exposed \
  tests.test_connectors.ConnectorTests.test_manifest_declared_metadata_policy_rejects_unsafe_shape \
  tests.test_executor.ExecutorTests.test_manifest_declared_external_metadata_is_projected_without_raw_values -v
```
