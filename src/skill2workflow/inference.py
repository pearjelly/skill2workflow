"""Conservative, shared prose vocabulary for Skill inference.

English terms match whole words; Chinese terms match substrings. Inference
never grants a connector binding. The returned term comes from this fixed
vocabulary rather than echoing arbitrary source prose.
"""

import re
from typing import Optional, Tuple

HUMAN_TERMS = (
    "approval", "approvals", "approve", "approved", "approver", "approves",
    "ask user", "user review", "user reviews", "wait for user",
    "human review", "human approval", "human confirmation",
    "confirm with user", "confirm with the user", "ask business owner to confirm",
    "审批", "审核", "批准", "人工确认", "人工复核", "用户确认", "等待确认",
)
VERIFY_TERMS = (
    "verify", "verification", "validate", "validation", "test", "tests",
    "check", "checks", "校验", "验证", "核对", "检查",
)
TOOL_TERMS = ("tool", "tools", "command", "commands", "run", "use")


def matched_term(text: str, terms: Tuple[str, ...]) -> Optional[str]:
    for term in terms:
        if re.search(r"[\u4e00-\u9fff]", term):
            if term in text:
                return term
        elif re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
            return term
    return None


def infer_step(text: str) -> Tuple[str, Optional[str]]:
    for node_type, terms in (("human_gate", HUMAN_TERMS), ("verification", VERIFY_TERMS)):
        term = matched_term(text, terms)
        if term is not None:
            return node_type, term
    return "step", None
