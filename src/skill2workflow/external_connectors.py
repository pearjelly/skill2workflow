"""Explicit external connector fixture loading."""

from __future__ import annotations

import os
import stat
import types
from pathlib import Path

from .connectors import ExternalConnector


MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES = 2 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024


def load_external_connector(path: Path) -> ExternalConnector:
    """Load one bounded, regular local connector fixture for this process."""
    path = Path(path).absolute()
    source = _read_fixture_source(path)
    module = types.ModuleType(f"_skill2workflow_external_{path.stem}")
    module.__file__ = str(path)
    module.__package__ = ""
    try:
        code = compile(source, str(path), "exec")
    except SyntaxError as error:
        raise ValueError(
            f"external connector file has invalid Python syntax: {path}"
        ) from error
    exec(code, module.__dict__)

    manifest = getattr(module, "MANIFEST", None)
    executor = getattr(module, "execute", None)
    preflight = getattr(module, "preflight", None)
    if manifest is None:
        raise ValueError(f"external connector fixture must define MANIFEST: {path}")
    if executor is None:
        raise ValueError(f"external connector fixture must define execute: {path}")
    if preflight is not None and not callable(preflight):
        raise ValueError(f"external connector fixture preflight must be callable: {path}")

    return ExternalConnector(manifest=manifest, executor=executor, preflight=preflight)


def _read_fixture_source(path: Path) -> str:
    """Read fixture source through a bounded, descriptor-bound no-follow path."""

    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError(f"external connector file not found: {path}") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError(
            f"external connector file must be a regular non-symlink file: {path}"
        )
    if before.st_size > MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES:
        raise ValueError(
            f"external connector file exceeds {MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES} bytes: {path}"
        )

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"external connector file cannot be loaded: {path}") from error

    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise ValueError(f"external connector file changed while being read: {path}")
        if opened.st_size > MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES:
            raise ValueError(
                f"external connector file exceeds {MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES} bytes: {path}"
            )

        chunks = []
        remaining = MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES:
            raise ValueError(
                f"external connector file exceeds {MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES} bytes: {path}"
            )

        after = path.lstat()
        if (
            after.st_dev != before.st_dev
            or after.st_ino != before.st_ino
            or after.st_size > MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES
        ):
            raise ValueError(f"external connector file changed while being read: {path}")
    except OSError as error:
        raise ValueError(f"external connector file cannot be loaded: {path}") from error
    finally:
        os.close(descriptor)

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"external connector file must be UTF-8: {path}") from error
