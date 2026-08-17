# Local JSON Run-State Boundary

Loop 170 hardens the dependency-light JSON run-state backend. SQLite remains
the required storage mode for the long-running service; this contract protects
local `run`, `resume`, inspection, and recovery paths that explicitly select
JSON storage.

## Fixed contract

Each JSON run-state document is capped at **8,388,608 bytes (8 MiB)** after
UTF-8 serialization. `JsonRunStore.save()` rejects a larger state before it is
written. `load`, complete listing, bounded listing, and interrupted-run
iteration read through a regular, non-symlink descriptor, use `O_NOFOLLOW`
when the platform provides it, bind the descriptor to the inspected
device/inode, read at most one byte beyond the bound, and recheck the path
after reading. A symlink, path replacement, growth race, or oversized document
fails closed before JSON normalization.

The state shape, run identifiers, JSON storage selection, and complete-list
compatibility APIs remain unchanged for documents within the bound. The
boundary limits memory and path-race exposure; it does not encrypt business
state, redact local JSON files, add multi-process locking, or change the
SQLite projections used by the service.

## Verification

Focused storage coverage:

```bash
PYTHONPATH=src python3 -m unittest tests.test_storage -v
```

The regression suite covers pre-open size rejection, bounded writes, symlink
rejection, path replacement, and read growth beyond the fixed window.
