"""Pure, fixed-error boundary for author-declared trigger input schemas."""

import copy

from .input_schema import validate_input_schema_contract


SKILL_INPUT_SCHEMA_ERROR = 'Invalid Skill input schema declaration'


def skill_input_schema_contract(schema):
    """Validate and copy the existing DSL subset without I/O or coercion."""
    try:
        if validate_input_schema_contract(schema):
            raise ValueError()
        return copy.deepcopy(schema)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError(SKILL_INPUT_SCHEMA_ERROR) from error
