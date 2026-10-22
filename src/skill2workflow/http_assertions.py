"""Bounded JSON response assertions; no expressions or executable source."""

import json
import math
import re


CONFIG_ERROR = "http assertion configuration is invalid"


def validate_http_assertion_binding(binding):
    """Return a fixed error or None, before credentials or transport."""
    try:
        request = binding.get("request")
        checks = binding.get("assertions")
        if not isinstance(request, dict) or request.get("method", "GET") != "GET":
            return CONFIG_ERROR
        if "body" in request or request.get("response_mode", "full") != "full":
            return CONFIG_ERROR
        mappings = request.get("input_mapping", [])
        if not isinstance(mappings, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("to"), str)
            or not item["to"].startswith("/query/") for item in mappings
        ):
            return CONFIG_ERROR
        if not isinstance(checks, list) or not 1 <= len(checks) <= 16:
            return CONFIG_ERROR
        for check in checks:
            if not isinstance(check, dict) or set(check) != {"path", "equals"}:
                return CONFIG_ERROR
            path, expected = check["path"], check["equals"]
            if not isinstance(path, str) or len(path.encode("utf-8")) > 1024:
                return CONFIG_ERROR
            if path and (not path.startswith("/") or path.count("/") > 32):
                return CONFIG_ERROR
            if re.search(r"~(?![01])", path):
                return CONFIG_ERROR
            if expected is not None and type(expected) not in (str, int, float, bool):
                return CONFIG_ERROR
            if len(json.dumps(expected, allow_nan=False, ensure_ascii=False).encode("utf-8")) > 4096:
                return CONFIG_ERROR
    except (AttributeError, ValueError, TypeError, OverflowError, UnicodeError):
        return CONFIG_ERROR
    return None


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _number(value):
    if len(value) > 128:
        raise ValueError("oversized number")
    result = float(value) if any(char in value for char in ".eE") else int(value)
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("nonfinite number")
    return result


def _constant(value):
    raise ValueError("invalid constant")


def evaluate_http_assertions(payload, checks):
    """Return only a fixed outcome; never return response or expected values."""
    try:
        document = json.loads(payload, object_pairs_hook=_object, parse_int=_number,
                              parse_float=_number, parse_constant=_constant)
    except (ValueError, TypeError, RecursionError, OverflowError):
        return "http assertion response is invalid"
    for check in checks:
        actual = document
        try:
            for token in check["path"].split("/")[1:] if check["path"] else []:
                token = token.replace("~1", "/").replace("~0", "~")
                if isinstance(actual, dict):
                    actual = actual[token]
                elif isinstance(actual, list) and re.fullmatch(r"0|[1-9][0-9]{0,8}", token):
                    actual = actual[int(token)]
                else:
                    return "http assertion did not match"
        except (KeyError, IndexError):
            return "http assertion did not match"
        expected = check["equals"]
        # JSON numbers compare numerically; booleans never equal 0 or 1.
        if (isinstance(actual, bool) != isinstance(expected, bool)
                or type(actual) not in (str, int, float, bool, type(None))
                or actual != expected):
            return "http assertion did not match"
    return None
