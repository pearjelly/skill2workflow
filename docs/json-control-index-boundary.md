# Local JSON Control-Index Boundary

Loop 171 hardens the dependency-light JSON control-plane registry. The
self-hosted service still requires SQLite; this contract protects explicit
local JSON control-plane use for evaluation and small local deployments.

## Fixed contract

`workflows/index.json` is capped at **8,388,608 bytes (8 MiB)** after UTF-8
serialization. `JsonControlStore.save_index()` rejects a larger index before
writing it. `load_index()` and SQLite's one-time JSON-to-SQLite import path
read the index through a regular, non-symlink descriptor, use `O_NOFOLLOW`
when available, bind the descriptor to the inspected device/inode, read at
most one byte beyond the bound, and recheck path identity and size after the
read. Oversized, linked, replaced, or growing indexes fail closed before JSON
normalization.

The registry record shape, JSON storage selection, and complete-list
compatibility behavior remain unchanged for indexes within the bound. The
boundary does not encrypt or redact local control state, add multi-process
locking, bound workflow artifact payloads, or change SQLite registry
projections.

## Verification

```bash
PYTHONPATH=src python3 -m unittest tests.test_storage -v
```

The storage regression suite covers pre-open size rejection, bounded writes,
symlink rejection, path replacement, and read growth beyond the fixed window.
