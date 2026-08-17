# External Connector Fixture Loading Boundary

The explicit `--connector-fixture` path is a local operator convenience for
reviewed connector code. It is not a plugin marketplace, package installer, or
service-side extension mechanism.

## Source handoff contract

`load_external_connector(path)` accepts one source file and enforces these
properties before Python compilation:

- the final path is a regular, non-symbolic-link file;
- the source is no larger than 2 MiB and decodes as UTF-8;
- the file is opened with `O_NOFOLLOW` where the host provides it;
- the opened descriptor must retain the original device and inode identity;
- the bounded read must not observe a replacement or post-read growth; and
- source is compiled from the bounded in-memory bytes, so the loader does not
  reopen the path through a second importlib read.

The loader's result is still validated by `ConnectorRuntime`. The normalized
connector result remains subject to the existing 1 MiB JSON envelope, and
credential values, mapped business values, and raw provider payloads remain
outside durable run state and audit evidence.

This is a file-handoff boundary, not a Python sandbox. A fixture executes with
the privileges of the invoking local process and may perform arbitrary local
side effects during import or execution. Operators must review the file and
run it only in a controlled workspace.

## Scope

The boundary applies only to local `run`, `resume`, and `bundle-run` commands
when the operator supplies `--connector-fixture`. The default built-in
registry, long-running service, remote trigger API, automatic discovery, and
package installation do not load connector code dynamically. The Workflow DSL
remains the execution authority; the fixture cannot mutate the published
artifact through the runtime contract.

## Verification

Focused loader tests cover regular fixture execution, symbolic-link and
non-regular rejection, the 2 MiB source bound, invalid UTF-8, and normalized
syntax errors:

```bash
PYTHONPATH=src python3 -m unittest tests.test_external_connectors -v
```

The installed CLI path remains covered by the external connector smoke and
the `run`/`resume`/`bundle-run` CLI tests.
