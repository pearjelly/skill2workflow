"""Secret hygiene checks for committed JSON fixtures."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


SECRET_KEY_NAMES = {
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "cookie",
    "password",
    "passwd",
    "private_key",
    "refresh_token",
    "secret",
    "set_cookie",
    "token",
    "x_api_key",
}

PLACEHOLDER_VALUES = {
    "",
    "<redacted>",
    "redacted",
    "placeholder",
    "example",
    "example-token",
    "token-placeholder",
    "dummy",
    "dummy-token",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE),
]

PRIVATE_DIRECTORY_NAMES = {"private", "secret", "secrets"}
PRIVATE_FILE_NAMES = {
    ".env",
    "credential.json",
    "credentials.json",
    "secret.json",
    "secrets.json",
}
PRIVATE_SUFFIXES = {
    ".db",
    ".jsonl",
    ".key",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
}
PUBLIC_MEDIA_SUFFIXES = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".wav",
    ".webp",
    ".zip",
}
MAX_JSON_BYTES = 2 * 1024 * 1024


Finding = Dict[str, str]


def scan_json_value(value: Any, source: str = "<memory>") -> List[Finding]:
    """Return secret-like findings for a loaded JSON-compatible value."""

    findings: List[Finding] = []
    _scan_value(value, source=source, path="$", parent_key="", findings=findings)
    return findings


def scan_json_paths(paths: Sequence[Path]) -> List[Finding]:
    """Scan JSON files and directories, returning all findings."""

    findings: List[Finding] = []
    for path in _expand_paths(paths):
        content, rejection = _read_json_candidate(path)
        if rejection:
            reason, marker = rejection
            findings.append(_json_file_finding(path, reason, marker))
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(
                _json_file_finding(
                    path, "JSON file is not valid UTF-8", "<redacted>"
                )
            )
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            findings.append(
                _json_file_finding(path, "invalid JSON", "<redacted>")
            )
            continue
        findings.extend(scan_json_value(value, source=str(path)))
    return findings


def scan_repository_paths(repo_root: Path, paths: Sequence[Path]) -> List[Finding]:
    """Reject private or misplaced binary artifacts without reading them."""

    repo_root = Path(repo_root).resolve()
    findings: List[Finding] = []
    for candidate in paths:
        path = Path(candidate)
        declared = path if path.is_absolute() else repo_root / path
        absolute = declared.resolve()
        try:
            relative = absolute.relative_to(repo_root)
        except ValueError:
            findings.append(_path_finding(path, "path escapes repository"))
            continue

        reason = _repository_path_rejection(relative, declared)
        if reason:
            findings.append(_path_finding(declared, reason))
    return findings


def scan_repository(repo_root: Path):
    """Scan every tracked or unignored candidate without exposing values."""

    repo_root = Path(repo_root).resolve()
    paths = _git_candidate_paths(repo_root)
    path_findings = scan_repository_paths(repo_root, paths)
    rejected = {finding["source"] for finding in path_findings}
    json_paths = [
        path
        for path in paths
        if path.suffix.lower() == ".json"
        and str(path) not in rejected
        and path.is_file()
        and not path.is_symlink()
    ]
    return paths, [*path_findings, *scan_json_paths(json_paths)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="secret_hygiene",
        description="Scan JSON fixtures or repository candidates for secret-like artifacts.",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="JSON files or directories to scan.")
    parser.add_argument(
        "--repository-root",
        type=Path,
        help="Scan tracked and unignored files below this Git repository.",
    )
    args = parser.parse_args(argv)

    if args.repository_root is not None:
        if args.paths:
            parser.error("paths cannot be combined with --repository-root")
        try:
            expanded, findings = scan_repository(args.repository_root)
        except (OSError, RuntimeError, ValueError):
            payload = {
                "ok": False,
                "scanned": [],
                "findings": [
                    {
                        "source": "<repository>",
                        "path": "$",
                        "reason": "repository candidates could not be enumerated",
                        "value_preview": "<not-read>",
                    }
                ],
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
    else:
        if not args.paths:
            parser.error("at least one JSON path or --repository-root is required")
        expanded = _expand_paths(args.paths)
        findings = scan_json_paths(args.paths)
    scanned_paths = [str(path) for path in expanded]
    payload = {
        "ok": not findings,
        "scanned": scanned_paths,
        "findings": findings,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


def _scan_value(value: Any, source: str, path: str, parent_key: str, findings: List[Finding]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            child_path = _join_path(path, key_text)
            if isinstance(item, str):
                _scan_string(item, source=source, path=child_path, key=key_text, findings=findings)
            else:
                _scan_value(item, source=source, path=child_path, parent_key=key_text, findings=findings)
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            child_path = f"{path}[{index}]"
            if isinstance(item, str):
                _scan_string(item, source=source, path=child_path, key=parent_key, findings=findings)
            else:
                _scan_value(item, source=source, path=child_path, parent_key=parent_key, findings=findings)
        return

    if isinstance(value, str):
        _scan_string(value, source=source, path=path, key=parent_key, findings=findings)


def _scan_string(value: str, source: str, path: str, key: str, findings: List[Finding]) -> None:
    if _is_placeholder(value):
        return

    key_is_secret = _is_secret_key(key)
    value_is_secret = _is_secret_value(value)
    if key_is_secret and value_is_secret:
        reason = "secret-like key and value"
    elif key_is_secret:
        reason = "secret-like key"
    elif value_is_secret:
        reason = "secret-like value"
    else:
        return

    findings.append(
        {
            "source": source,
            "path": path,
            "reason": reason,
            "value_preview": _preview(value),
        }
    )


def _expand_paths(paths: Iterable[Path]) -> List[Path]:
    expanded: List[Path] = []
    for path in paths:
        path = Path(path)
        if path.is_dir():
            expanded.extend(sorted(item for item in path.rglob("*.json") if item.is_file()))
        else:
            expanded.append(path)
    return sorted(expanded)


def _git_candidate_paths(repo_root: Path) -> List[Path]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("git candidate enumeration failed")
    relative_paths = [
        Path(os.fsdecode(value))
        for value in completed.stdout.split(b"\0")
        if value
    ]
    return sorted(repo_root / path for path in relative_paths)


def _read_json_candidate(path: Path):
    path = Path(path)
    if path.is_symlink():
        return None, ("symbolic JSON path is not allowed", "<not-read>")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None, ("JSON file is unavailable", "<not-read>")
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return None, ("JSON file is unavailable", "<not-read>")
        if metadata.st_size > MAX_JSON_BYTES:
            return None, ("JSON file exceeds scan size limit", "<not-read>")
        chunks = []
        remaining = MAX_JSON_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > MAX_JSON_BYTES:
            return None, ("JSON file exceeds scan size limit", "<not-read>")
        return content, None
    except OSError:
        return None, ("JSON file is unavailable", "<not-read>")
    finally:
        os.close(descriptor)


def _repository_path_rejection(relative: Path, absolute: Path) -> str:
    lowered_parts = {part.lower() for part in relative.parts[:-1]}
    name = relative.name.lower()
    suffix = relative.suffix.lower()
    if absolute.is_symlink():
        return "symbolic links are not public artifacts"
    if PRIVATE_DIRECTORY_NAMES.intersection(lowered_parts):
        return "private directory is not a public artifact"
    if name in PRIVATE_FILE_NAMES or name.startswith(".env."):
        return "credential or environment file is not a public artifact"
    if suffix in PRIVATE_SUFFIXES:
        return "credential or runtime state suffix is not a public artifact"
    if suffix in PUBLIC_MEDIA_SUFFIXES and relative.parts[:2] != (
        "docs",
        "assets",
    ):
        return "binary media must be reviewed under docs/assets"
    return ""


def _path_finding(path: Path, reason: str) -> Finding:
    return {
        "source": str(path),
        "path": "$",
        "reason": reason,
        "value_preview": "<not-read>",
    }


def _json_file_finding(path: Path, reason: str, marker: str) -> Finding:
    return {
        "source": str(path),
        "path": "$",
        "reason": reason,
        "value_preview": marker,
    }


def _is_secret_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return normalized in SECRET_KEY_NAMES


def _is_secret_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS)


def _is_placeholder(value: str) -> bool:
    normalized = _strip_auth_scheme(value.strip()).strip().lower()
    return normalized in PLACEHOLDER_VALUES


def _strip_auth_scheme(value: str) -> str:
    pieces = value.split(None, 1)
    if len(pieces) == 2 and pieces[0].lower() in {"bearer", "basic", "token"}:
        return pieces[1]
    return value


def _join_path(path: str, key: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", key):
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key)}]"


def _preview(value: str) -> str:
    return "<redacted>"


if __name__ == "__main__":
    raise SystemExit(main())
