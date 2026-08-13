"""Narrow, deterministic trigger-input contracts for published workflows.

The project intentionally implements a small JSON-Schema-like subset instead
of claiming full JSON Schema support.  The subset is enough to make business
inputs explicit while keeping validation bounded, dependency-free, and safe to
run before a durable trigger idempotency claim or an external connector call.
"""

from __future__ import annotations

import json
import math
from typing import Dict, List, Optional, Sequence


INPUT_SCHEMA_MAX_BYTES = 64 * 1024
INPUT_SCHEMA_MAX_DEPTH = 8
INPUT_SCHEMA_MAX_PROPERTIES = 128
INPUT_SCHEMA_MAX_ENUM_ITEMS = 128
_SUPPORTED_TYPES = {"array", "boolean", "integer", "null", "number", "object", "string"}
_SUPPORTED_KEYS = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "enum",
}
_OBJECT_KEYS = {"properties", "required", "additionalProperties"}
_ARRAY_KEYS = {"items"}
_STRING_KEYS = {"minLength", "maxLength"}
_NUMBER_KEYS = {"minimum", "maximum"}


class InputSchemaValidationError(ValueError):
    """Raised when a trigger input violates a published input contract."""

    def __init__(self, code: str, message: str, path: Sequence[object]):
        self.code = code
        self.path = list(path)
        super().__init__(message)


def validate_input_schema_contract(
    schema: object,
    path: Optional[Sequence[object]] = None,
) -> List[Dict[str, object]]:
    """Return structured errors for the supported input-schema subset."""

    root_path = list(path or ["input_schema"])
    errors: List[Dict[str, object]] = []
    if not isinstance(schema, dict):
        return [_error("input_schema_invalid", "input_schema must be an object", root_path)]

    try:
        encoded = json.dumps(
            schema,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        return [_error("input_schema_invalid", "input_schema must be finite JSON", root_path)]
    if len(encoded) > INPUT_SCHEMA_MAX_BYTES:
        errors.append(
            _error(
                "input_schema_too_large",
                f"input_schema must be at most {INPUT_SCHEMA_MAX_BYTES} UTF-8 bytes",
                root_path,
            )
        )

    _validate_schema_node(schema, root_path, errors, depth=0, require_object=True)
    return errors


def validate_trigger_input(schema: object, value: object) -> None:
    """Validate a normalized trigger value against a published contract."""

    if schema is None:
        return
    contract_errors = validate_input_schema_contract(schema)
    if contract_errors:
        first = contract_errors[0]
        raise InputSchemaValidationError(
            str(first["code"]),
            "published workflow input_schema is invalid",
            first.get("path", ["input_schema"]),
        )
    errors: List[Dict[str, object]] = []
    _validate_value(schema, value, ["input"], errors)
    if errors:
        first = errors[0]
        raise InputSchemaValidationError(
            str(first["code"]),
            str(first["message"]),
            first.get("path", ["input"]),
        )


def _validate_schema_node(
    schema: object,
    path: List[object],
    errors: List[Dict[str, object]],
    depth: int,
    require_object: bool = False,
) -> None:
    if depth > INPUT_SCHEMA_MAX_DEPTH:
        errors.append(
            _error(
                "input_schema_depth_exceeded",
                f"input_schema nesting must be at most {INPUT_SCHEMA_MAX_DEPTH} levels",
                path,
            )
        )
        return
    if not isinstance(schema, dict):
        errors.append(_error("input_schema_node_invalid", "input_schema nodes must be objects", path))
        return

    for key in sorted(set(schema) - _SUPPORTED_KEYS):
        errors.append(
            _error(
                "input_schema_keyword_unsupported",
                f"input_schema keyword is not supported: {key}",
                path + [key],
            )
        )

    schema_type = schema.get("type")
    if not isinstance(schema_type, str) or schema_type not in _SUPPORTED_TYPES:
        errors.append(
            _error(
                "input_schema_type_invalid",
                "input_schema.type must be one of array, boolean, integer, null, number, object, string",
                path + ["type"],
            )
        )
        return
    if require_object and schema_type != "object":
        errors.append(
            _error(
                "input_schema_root_invalid",
                "input_schema root type must be object",
                path + ["type"],
            )
        )

    if "enum" in schema:
        enum = schema.get("enum")
        if not isinstance(enum, list) or not enum or len(enum) > INPUT_SCHEMA_MAX_ENUM_ITEMS:
            errors.append(
                _error(
                    "input_schema_enum_invalid",
                    f"input_schema.enum must be a non-empty list of at most {INPUT_SCHEMA_MAX_ENUM_ITEMS} items",
                    path + ["enum"],
                )
            )
        else:
            try:
                json.dumps(enum, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError, OverflowError, RecursionError):
                errors.append(
                    _error("input_schema_enum_invalid", "input_schema.enum must be finite JSON", path + ["enum"])
                )

    allowed_for_type = {
        "object": _OBJECT_KEYS,
        "array": _ARRAY_KEYS,
        "string": _STRING_KEYS,
        "integer": _NUMBER_KEYS,
        "number": _NUMBER_KEYS,
        "boolean": set(),
        "null": set(),
    }[schema_type]
    for key in sorted(set(schema) & (_OBJECT_KEYS | _ARRAY_KEYS | _STRING_KEYS | _NUMBER_KEYS)):
        if key not in allowed_for_type:
            errors.append(
                _error(
                    "input_schema_keyword_invalid",
                    f"input_schema keyword {key} is not valid for type {schema_type}",
                    path + [key],
                )
            )

    if schema_type == "object":
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            errors.append(_error("input_schema_properties_invalid", "input_schema.properties must be an object", path + ["properties"]))
        elif len(properties) > INPUT_SCHEMA_MAX_PROPERTIES:
            errors.append(
                _error(
                    "input_schema_properties_too_many",
                    f"input_schema.properties must contain at most {INPUT_SCHEMA_MAX_PROPERTIES} properties",
                    path + ["properties"],
                )
            )
        else:
            for name, child in properties.items():
                if not isinstance(name, str) or not name or len(name.encode("utf-8")) > 128:
                    errors.append(
                        _error(
                            "input_schema_property_name_invalid",
                            "input_schema property names must be non-empty strings of at most 128 UTF-8 bytes",
                            path + ["properties"],
                        )
                    )
                    continue
                _validate_schema_node(child, path + ["properties", name], errors, depth + 1)

        required = schema.get("required", [])
        if not isinstance(required, list) or any(not isinstance(name, str) or not name for name in required):
            errors.append(_error("input_schema_required_invalid", "input_schema.required must be a list of property names", path + ["required"]))
        elif len(required) != len(set(required)):
            errors.append(_error("input_schema_required_invalid", "input_schema.required must not contain duplicates", path + ["required"]))
        elif isinstance(properties, dict):
            unknown_required = sorted(set(required) - set(properties))
            if unknown_required:
                errors.append(_error("input_schema_required_unknown", "input_schema.required must reference declared properties", path + ["required"]))

        additional = schema.get("additionalProperties", True)
        if not isinstance(additional, bool):
            errors.append(_error("input_schema_additional_properties_invalid", "input_schema.additionalProperties must be a boolean", path + ["additionalProperties"]))
    elif schema_type == "array" and "items" in schema:
        _validate_schema_node(schema.get("items"), path + ["items"], errors, depth + 1)

    if schema_type == "string":
        _validate_nonnegative_integer(schema, "minLength", path, errors)
        _validate_nonnegative_integer(schema, "maxLength", path, errors)
        if _valid_int(schema.get("minLength")) and _valid_int(schema.get("maxLength")) and schema["minLength"] > schema["maxLength"]:
            errors.append(_error("input_schema_length_range_invalid", "input_schema.minLength must not exceed maxLength", path))
        if _valid_int(schema.get("maxLength")) and schema["maxLength"] > 1024 * 1024:
            errors.append(_error("input_schema_length_range_invalid", "input_schema.maxLength is too large", path + ["maxLength"]))
    if schema_type in {"integer", "number"}:
        _validate_number_bound(schema, "minimum", path, errors)
        _validate_number_bound(schema, "maximum", path, errors)
        if _valid_number(schema.get("minimum")) and _valid_number(schema.get("maximum")) and schema["minimum"] > schema["maximum"]:
            errors.append(_error("input_schema_number_range_invalid", "input_schema.minimum must not exceed maximum", path))


def _validate_value(schema: Dict[str, object], value: object, path: List[object], errors: List[Dict[str, object]]) -> None:
    schema_type = schema.get("type")
    if not _matches_type(schema_type, value):
        errors.append(_error("input_type", f"trigger input at {_json_pointer(path)} has the wrong type", path))
        return
    enum = schema.get("enum")
    if isinstance(enum, list) and not any(_json_equal(value, candidate) for candidate in enum):
        errors.append(_error("input_enum", f"trigger input at {_json_pointer(path)} is not an allowed value", path))
        return
    if schema_type == "object":
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return
        required = schema.get("required", [])
        for name in required if isinstance(required, list) else []:
            if name not in value:
                errors.append(_error("input_required", f"required trigger input property is missing at {_json_pointer(path + [name])}", path + [name]))
                return
        additional = schema.get("additionalProperties", True)
        if additional is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                errors.append(_error("input_unknown_property", f"trigger input contains an undeclared property at {_json_pointer(path + [unknown[0]])}", path + [unknown[0]]))
                return
        for name, child in properties.items():
            if name in value and isinstance(child, dict):
                _validate_value(child, value[name], path + [name], errors)
                if errors:
                    return
    elif schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(value):
                _validate_value(items, item, path + [index], errors)
                if errors:
                    return
    elif schema_type == "string":
        length = len(value)
        if _valid_int(schema.get("minLength")) and length < schema["minLength"]:
            errors.append(_error("input_string_too_short", f"trigger input at {_json_pointer(path)} is shorter than allowed", path))
        elif _valid_int(schema.get("maxLength")) and length > schema["maxLength"]:
            errors.append(_error("input_string_too_long", f"trigger input at {_json_pointer(path)} is longer than allowed", path))
    elif schema_type in {"integer", "number"}:
        if _valid_number(schema.get("minimum")) and value < schema["minimum"]:
            errors.append(_error("input_number_too_small", f"trigger input at {_json_pointer(path)} is below the allowed minimum", path))
        elif _valid_number(schema.get("maximum")) and value > schema["maximum"]:
            errors.append(_error("input_number_too_large", f"trigger input at {_json_pointer(path)} exceeds the allowed maximum", path))


def _matches_type(schema_type: object, value: object) -> bool:
    if schema_type == "null":
        return value is None
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    return False


def _validate_nonnegative_integer(schema: Dict[str, object], key: str, path: List[object], errors: List[Dict[str, object]]) -> None:
    if key in schema and (not _valid_int(schema.get(key)) or schema[key] < 0):
        errors.append(_error("input_schema_keyword_invalid", f"input_schema.{key} must be a non-negative integer", path + [key]))


def _validate_number_bound(schema: Dict[str, object], key: str, path: List[object], errors: List[Dict[str, object]]) -> None:
    if key in schema and not _valid_number(schema.get(key)):
        errors.append(_error("input_schema_keyword_invalid", f"input_schema.{key} must be a finite number", path + [key]))


def _valid_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _json_equal(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return type(left) is type(right) and left == right


def _json_pointer(path: Sequence[object]) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in path)


def _error(code: str, message: str, path: Sequence[object]) -> Dict[str, object]:
    return {"code": code, "message": message, "path": list(path), "severity": "error"}
