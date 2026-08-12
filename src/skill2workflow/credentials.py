"""Local credential provider boundary."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Dict


MAX_DIRECTORY_CREDENTIAL_BYTES = 64 * 1024


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


class DirectoryCredentialProvider:
    """Resolve credential handles from separately mounted files on every use."""

    _HANDLE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,127}\Z")

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        if not self.directory.is_absolute():
            raise ValueError("credential directory must be an absolute path")
        if not self.is_ready():
            raise ValueError(
                "credential directory must be a private non-symlink directory"
            )

    def is_ready(self) -> bool:
        try:
            details = self.directory.lstat()
        except OSError:
            return False
        return bool(
            stat.S_ISDIR(details.st_mode)
            and not stat.S_ISLNK(details.st_mode)
            and not (stat.S_IMODE(details.st_mode) & 0o077)
        )

    def resolve(self, handle: str) -> str:
        handle_text = str(handle or "")
        if not self._HANDLE.fullmatch(handle_text):
            raise CredentialResolutionError(f"credential handle is invalid: {handle_text}")
        try:
            value = _read_directory_credential(self.directory, handle_text)
        except (OSError, UnicodeDecodeError, ValueError):
            raise CredentialResolutionError(
                f"credential handle not found: {handle_text}"
            ) from None
        if value.endswith("\r\n"):
            value = value[:-2]
        elif value.endswith("\n"):
            value = value[:-1]
        if not value:
            raise CredentialResolutionError(
                f"credential handle not found: {handle_text}"
            )
        return value


def _read_directory_credential(directory: Path, handle: str) -> str:
    root_before = directory.lstat()
    if (
        not stat.S_ISDIR(root_before.st_mode)
        or stat.S_ISLNK(root_before.st_mode)
        or stat.S_IMODE(root_before.st_mode) & 0o077
    ):
        raise OSError("unsafe credential directory")
    target = directory / handle
    target_before = target.lstat()
    if (
        not stat.S_ISREG(target_before.st_mode)
        or stat.S_ISLNK(target_before.st_mode)
        or stat.S_IMODE(target_before.st_mode) & 0o077
    ):
        raise OSError("unsafe credential file")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags)
    try:
        opened = os.fstat(descriptor)
        root_after = directory.lstat()
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != target_before.st_dev
            or opened.st_ino != target_before.st_ino
            or root_after.st_dev != root_before.st_dev
            or root_after.st_ino != root_before.st_ino
            or not stat.S_ISDIR(root_after.st_mode)
            or stat.S_ISLNK(root_after.st_mode)
            or stat.S_IMODE(root_after.st_mode) & 0o077
            or stat.S_IMODE(opened.st_mode) & 0o077
        ):
            raise OSError("credential file changed while being read")
        if opened.st_size > MAX_DIRECTORY_CREDENTIAL_BYTES:
            raise OSError("credential file exceeds size limit")
        chunks = []
        remaining = MAX_DIRECTORY_CREDENTIAL_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(4096, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > MAX_DIRECTORY_CREDENTIAL_BYTES:
            raise OSError("credential file exceeds size limit")
    finally:
        os.close(descriptor)
    return payload.decode("utf-8")


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
