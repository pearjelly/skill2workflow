"""Explicit external connector fixture loading."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .connectors import ExternalConnector


def load_external_connector(path: Path) -> ExternalConnector:
    """Load one external connector fixture from an explicit Python file path."""
    path = Path(path).resolve()
    if not path.exists():
        raise ValueError(f"external connector file not found: {path}")

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"external connector file cannot be loaded: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

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
