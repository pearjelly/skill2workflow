"""Secret hygiene checks for committed JSON fixtures."""

from __future__ import annotations

import argparse
import json
import re
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
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            findings.append(
                {
                    "source": str(path),
                    "path": "$",
                    "reason": "invalid JSON",
                    "value_preview": str(error),
                }
            )
            continue
        findings.extend(scan_json_value(value, source=str(path)))
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="secret_hygiene",
        description="Scan committed JSON fixtures for obvious secret-like values.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="JSON files or directories to scan.")
    args = parser.parse_args(argv)

    scanned_paths = [str(path) for path in _expand_paths(args.paths)]
    findings = scan_json_paths(args.paths)
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
    if len(value) <= 12:
        return value
    return f"{value[:12]}..."


if __name__ == "__main__":
    raise SystemExit(main())
