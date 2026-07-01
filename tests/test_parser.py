from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from skill2workflow.parser import parse_skill_file


class ParserTests(TestCase):
    def test_parse_standard_skill_into_ir(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(
                dedent(
                    """\
                    ---
                    name: approval-flow
                    description: Convert approval work into a controlled workflow.
                    ---

                    <HARD-GATE>
                    Do NOT publish until the user approves the draft.
                    </HARD-GATE>

                    ## Checklist

                    1. Explore project context
                    2. Draft workflow
                    3. Ask user for approval
                    4. Publish workflow
                    """
                ),
                encoding="utf-8",
            )

            ir = parse_skill_file(path)

        self.assertEqual(ir["metadata"]["name"], "approval-flow")
        self.assertEqual(
            ir["metadata"]["description"],
            "Convert approval work into a controlled workflow.",
        )
        self.assertEqual(
            ir["hard_gates"],
            ["Do NOT publish until the user approves the draft."],
        )
        self.assertEqual(
            ir["ordered_steps"],
            [
                "Explore project context",
                "Draft workflow",
                "Ask user for approval",
                "Publish workflow",
            ],
        )
        self.assertEqual(
            ir["ordered_step_details"][0],
            {
                "title": "Explore project context",
                "detail": "",
                "line": 12,
                "section": "Checklist",
            },
        )
        self.assertNotIn("## Checklist", ir["verification_rules"])
        self.assertNotIn("# Approval Flow Skill", ir["human_gates"])

    def test_parse_checkbox_checklist_without_checkbox_marker(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(
                dedent(
                    """\
                    ---
                    name: tdd
                    description: Test-first workflow.
                    ---

                    ## Verification Checklist

                    - [ ] Every new function has a test
                    - [x] Watched each test fail before implementing
                    - [ ] All tests pass
                    """
                ),
                encoding="utf-8",
            )

            ir = parse_skill_file(path)

        self.assertEqual(
            ir["ordered_steps"],
            [
                "Every new function has a test",
                "Watched each test fail before implementing",
                "All tests pass",
            ],
        )

    def test_parse_checklist_step_details_from_bold_title_and_dash_detail(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(
                dedent(
                    """\
                    ---
                    name: brainstorming
                    description: Design workflow.
                    ---

                    ## Checklist

                    1. **Explore project context** — check files, docs, recent commits
                    2. **Ask clarifying questions** - one at a time
                    """
                ),
                encoding="utf-8",
            )

            ir = parse_skill_file(path)

        self.assertEqual(
            ir["ordered_step_details"],
            [
                {
                    "title": "Explore project context",
                    "detail": "check files, docs, recent commits",
                    "line": 8,
                    "section": "Checklist",
                },
                {
                    "title": "Ask clarifying questions",
                    "detail": "one at a time",
                    "line": 9,
                    "section": "Checklist",
                },
            ],
        )

    def test_parser_ignores_fenced_code_for_rule_hints(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(
                dedent(
                    """\
                    ---
                    name: diagram-heavy
                    description: Skill with process diagrams.
                    ---

                    ## Checklist

                    1. Ask user for approval

                    ## Process Flow

                    ```dot
                    "User approves design?" [shape=diamond];
                    "Verify tests" -> "User approves design?";
                    ```

                    ## Verification

                    - Verify final output before completion.
                    """
                ),
                encoding="utf-8",
            )

            ir = parse_skill_file(path)

        self.assertEqual(ir["human_gates"], ["1. Ask user for approval"])
        self.assertEqual(ir["verification_rules"], ["- Verify final output before completion."])

    def test_human_gate_hints_do_not_treat_self_review_as_human_approval(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(
                dedent(
                    """\
                    ---
                    name: review-gates
                    description: Distinguish self-review from user approval.
                    ---

                    ## Checklist

                    1. Spec self-review
                    2. User reviews written spec
                    3. Wait for user approval
                    """
                ),
                encoding="utf-8",
            )

            ir = parse_skill_file(path)

        self.assertEqual(
            ir["human_gates"],
            [
                "2. User reviews written spec",
                "3. Wait for user approval",
            ],
        )

    def test_human_gate_hints_skip_verification_section(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(
                dedent(
                    """\
                    ---
                    name: approval-audit
                    description: Avoid mixing verification and approval gates.
                    ---

                    ## Checklist

                    1. Ask user for approval

                    ## Verification

                    - Check that all approval events were recorded.
                    """
                ),
                encoding="utf-8",
            )

            ir = parse_skill_file(path)

        self.assertEqual(ir["human_gates"], ["1. Ask user for approval"])
        self.assertEqual(
            ir["verification_rules"],
            ["- Check that all approval events were recorded."],
        )
