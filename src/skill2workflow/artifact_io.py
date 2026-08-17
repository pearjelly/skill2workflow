"""Bounded, descriptor-bound reads for immutable Workflow artifacts."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path


MAX_WORKFLOW_ARTIFACT_BYTES = 2 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024


def encode_workflow_artifact(value: object) -> bytes:
    """Serialize one published artifact without exceeding its byte boundary."""

    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > MAX_WORKFLOW_ARTIFACT_BYTES:
        raise ValueError(
            f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes"
        )
    return raw


def read_workflow_artifact(path: Path):
    """Read one artifact through a regular, no-follow descriptor.

    The path is checked before open, the opened descriptor is bound to the
    original device/inode, and the path is checked again after a bounded
    ``max+1`` read.  This prevents symlink, replacement, and growth races from
    turning an immutable artifact read into an unbounded allocation.
    """

    artifact_path = Path(path)
    try:
        before = artifact_path.lstat()
    except OSError:
        raise
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("workflow artifact must be a regular non-symlink file")
    if before.st_size > MAX_WORKFLOW_ARTIFACT_BYTES:
        raise ValueError(
            f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes"
        )

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(artifact_path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise ValueError("workflow artifact changed while being read")
        if opened.st_size > MAX_WORKFLOW_ARTIFACT_BYTES:
            raise ValueError(
                f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes"
            )

        chunks = []
        remaining = MAX_WORKFLOW_ARTIFACT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_WORKFLOW_ARTIFACT_BYTES:
            raise ValueError(
                f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes"
            )

        after = artifact_path.lstat()
        if after.st_dev != before.st_dev or after.st_ino != before.st_ino:
            raise ValueError("workflow artifact changed while being read")
        if after.st_size > MAX_WORKFLOW_ARTIFACT_BYTES:
            raise ValueError(
                f"workflow artifact exceeds {MAX_WORKFLOW_ARTIFACT_BYTES} bytes"
            )
    finally:
        os.close(descriptor)

    return json.loads(raw.decode("utf-8"))
