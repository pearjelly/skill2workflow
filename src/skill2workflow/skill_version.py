"""Pure, fixed-error boundary for author-declared Workflow DSL versions."""

import re


SKILL_WORKFLOW_VERSION_ERROR = 'Invalid Skill workflow version declaration'
_VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}')


def skill_workflow_version(value):
    """Validate one explicit authoring token without coercion or I/O."""
    if not isinstance(value, str) or len(value) > 128 or _VERSION.fullmatch(value) is None:
        raise ValueError(SKILL_WORKFLOW_VERSION_ERROR)
    return value
