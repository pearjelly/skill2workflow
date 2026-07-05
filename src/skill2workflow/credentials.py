"""Local credential provider boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class CredentialResolutionError(Exception):
    """Raised when a credential handle cannot be resolved."""


class StaticCredentialProvider:
    """Resolve credential handles from an in-memory mapping."""

    def __init__(self, credentials: Dict[str, str]):
        self._credentials = _validate_credentials(credentials)

    def resolve(self, handle: str) -> str:
        handle = str(handle or "")
        if handle not in self._credentials:
            raise CredentialResolutionError(f"credential handle not found: {handle}")
        return self._credentials[handle]


def load_credential_file(path: Path) -> StaticCredentialProvider:
    """Load local credentials from a JSON file."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("credential file must be a JSON object")
    credentials = payload.get("credentials", {})
    if not isinstance(credentials, dict):
        raise ValueError("credentials must be an object")
    return StaticCredentialProvider(credentials)


def _validate_credentials(credentials: Dict[str, str]) -> Dict[str, str]:
    if not isinstance(credentials, dict):
        raise ValueError("credentials must be an object")

    normalized: Dict[str, str] = {}
    for handle, value in credentials.items():
        handle_text = str(handle)
        if not handle_text:
            raise ValueError("credential handles must be non-empty strings")
        if not isinstance(value, str):
            raise ValueError("credential values must be strings")
        normalized[handle_text] = value
    return normalized
