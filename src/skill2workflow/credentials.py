"""Local credential provider boundary."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Dict
import urllib.request


MAX_DIRECTORY_CREDENTIAL_BYTES = 64 * 1024
MAX_CREDENTIAL_FILE_BYTES = 2 * 1024 * 1024
LARK_TENANT_ACCESS_TOKEN_URL = (
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
)
LARK_TENANT_ACCESS_TOKEN_TIMEOUT_SECONDS = 5.0
_CREDENTIAL_HANDLE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,127}\Z")


class CredentialResolutionError(Exception):
    """Raised when a credential handle cannot be resolved."""


def _require_credential_handle(value: object, label: str) -> str:
    handle = str(value or "")
    if not _CREDENTIAL_HANDLE.fullmatch(handle):
        raise ValueError(f"{label} is invalid")
    return handle


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

    _HANDLE = _CREDENTIAL_HANDLE

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


class LarkTenantAccessTokenCredentialProvider:
    """Derive one approved Feishu token without retaining provider credentials.

    The source provider remains responsible for secure private App Secret
    reads.  This narrow wrapper reserves its source handle and exposes only
    the configured public target handle to connector execution.
    """

    def __init__(
        self,
        source_provider,
        *,
        handle: str,
        app_id: str,
        app_secret_handle: str,
        token_transport=None,
    ):
        self.source_provider = source_provider
        configuration = validate_lark_tenant_access_token_config(
            handle=handle,
            app_id=app_id,
            app_secret_handle=app_secret_handle,
        )
        self.handle = configuration["handle"]
        self.app_id = configuration["app_id"]
        self.app_secret_handle = configuration["app_secret_handle"]
        self.token_transport = token_transport

    def is_ready(self) -> bool:
        checker = getattr(self.source_provider, "is_ready", None)
        return bool(checker()) if callable(checker) else True

    def resolve(self, handle: str) -> str:
        requested_handle = str(handle or "")
        if requested_handle == self.app_secret_handle:
            raise CredentialResolutionError(
                f"credential handle not found: {requested_handle}"
            )
        if requested_handle != self.handle:
            return self.source_provider.resolve(requested_handle)
        try:
            app_secret = self.source_provider.resolve(self.app_secret_handle)
            return _issue_lark_tenant_access_token(
                self.app_id,
                app_secret,
                token_transport=self.token_transport,
            )
        except (CredentialResolutionError, OSError, UnicodeDecodeError, ValueError):
            raise CredentialResolutionError(
                f"credential handle not found: {requested_handle}"
            ) from None


def validate_lark_tenant_access_token_config(
    *, handle: object, app_id: object, app_secret_handle: object
) -> Dict[str, str]:
    """Validate the non-secret static part of the narrow Feishu provider."""

    target = _require_credential_handle(handle, "lark tenant token handle")
    source = _require_credential_handle(
        app_secret_handle,
        "lark tenant token app_secret_handle",
    )
    if target == source:
        raise ValueError("lark tenant token handle and app_secret_handle must differ")
    if not isinstance(app_id, str) or not app_id or len(app_id.encode("utf-8")) > 256:
        raise ValueError("lark tenant token app_id is invalid")
    if "\r" in app_id or "\n" in app_id or "\x00" in app_id:
        raise ValueError("lark tenant token app_id is invalid")
    return {"handle": target, "app_id": app_id, "app_secret_handle": source}


def _issue_lark_tenant_access_token(
    app_id: str,
    app_secret: str,
    *,
    token_transport=None,
) -> str:
    """Exchange private App credentials directly for one in-memory token."""

    payload = json.dumps(
        {"app_id": app_id, "app_secret": app_secret},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        LARK_TENANT_ACCESS_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        if token_transport is None:
            response = urllib.request.build_opener(
                urllib.request.ProxyHandler({})
            ).open(request, timeout=LARK_TENANT_ACCESS_TOKEN_TIMEOUT_SECONDS)
        else:
            response = token_transport(request, LARK_TENANT_ACCESS_TOKEN_TIMEOUT_SECONDS)
        try:
            raw = response.read(MAX_DIRECTORY_CREDENTIAL_BYTES + 1)
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
    except Exception:
        raise ValueError("lark tenant token exchange failed") from None
    if not isinstance(raw, bytes) or len(raw) > MAX_DIRECTORY_CREDENTIAL_BYTES:
        raise ValueError("lark tenant token exchange failed")
    try:
        decoded = json.loads(raw.decode("utf-8"))
        token = decoded.get("tenant_access_token")
    except (AttributeError, TypeError, UnicodeDecodeError, ValueError):
        raise ValueError("lark tenant token exchange failed") from None
    if (
        not isinstance(decoded, dict)
        or type(decoded.get("code")) is not int
        or decoded.get("code") != 0
        or not isinstance(token, str)
        or not token
    ):
        raise ValueError("lark tenant token exchange failed")
    return token


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

    raw = _read_credential_file_payload(path)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("credential file is unavailable") from error
    if not isinstance(payload, dict):
        raise ValueError("credential file must be a JSON object")
    credentials = payload.get("credentials", {})
    if not isinstance(credentials, dict):
        raise ValueError("credentials must be an object")
    return StaticCredentialProvider(credentials)


def _read_credential_file_payload(path: Path) -> bytes:
    """Read one bounded local credential map without following path races."""

    credential_path = Path(path)
    try:
        before = credential_path.lstat()
    except OSError as error:
        raise ValueError("credential file is unavailable") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("credential file must be a regular non-symlink file")
    if before.st_size > MAX_CREDENTIAL_FILE_BYTES:
        raise ValueError(
            f"credential file exceeds {MAX_CREDENTIAL_FILE_BYTES} bytes"
        )

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(credential_path, flags)
    except OSError as error:
        raise ValueError("credential file is unavailable") from error
    try:
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != before.st_dev
                or opened.st_ino != before.st_ino
            ):
                raise ValueError("credential file changed while being read")
            if opened.st_size > MAX_CREDENTIAL_FILE_BYTES:
                raise ValueError(
                    f"credential file exceeds {MAX_CREDENTIAL_FILE_BYTES} bytes"
                )
            chunks = []
            remaining = MAX_CREDENTIAL_FILE_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > MAX_CREDENTIAL_FILE_BYTES:
                raise ValueError(
                    f"credential file exceeds {MAX_CREDENTIAL_FILE_BYTES} bytes"
                )
            after = credential_path.lstat()
            if after.st_dev != before.st_dev or after.st_ino != before.st_ino:
                raise ValueError("credential file changed while being read")
            if after.st_size > MAX_CREDENTIAL_FILE_BYTES:
                raise ValueError(
                    f"credential file exceeds {MAX_CREDENTIAL_FILE_BYTES} bytes"
                )
        except OSError as error:
            raise ValueError("credential file is unavailable") from error
    finally:
        os.close(descriptor)
    return raw


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
