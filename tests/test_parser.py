import os
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.parser import MAX_SKILL_FILE_BYTES, parse_skill_file, parse_skill_text


class ParserTests(TestCase):
    def test_parse_bounded_skill_text_uses_an_explicit_non_path_source(self):
        ir = parse_skill_text(
            "---\nname: local-preview\n---\n\n## Checklist\n\n1. Review draft\n",
            source_path="SKILL.md",
        )

        self.assertEqual(ir["metadata"]["name"], "local-preview")
        self.assertEqual(ir["source_path"], "SKILL.md")
        self.assertEqual(ir["ordered_steps"], ["Review draft"])

    def test_parse_skill_text_rejects_non_string_and_oversized_values(self):
        with self.assertRaisesRegex(ValueError, "text must be a string"):
            parse_skill_text(None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "must be valid UTF-8"):
            parse_skill_text("\ud800")
        with self.assertRaisesRegex(ValueError, f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes"):
            parse_skill_text("x" * (MAX_SKILL_FILE_BYTES + 1))

    def test_parse_rejects_oversized_skill_before_opening(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_bytes(b"# skill\n" + b"x" * MAX_SKILL_FILE_BYTES)

            with patch("skill2workflow.parser.os.open") as open_file:
                with self.assertRaisesRegex(
                    ValueError,
                    f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes",
                ):
                    parse_skill_file(path)

            open_file.assert_not_called()

    def test_parse_rejects_symlink_and_path_replacement(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "SKILL.md"
            outside = root / "outside.md"
            outside.write_text("# outside", encoding="utf-8")
            path.symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                parse_skill_file(path)

            path.unlink()
            path.write_text("# first", encoding="utf-8")
            replacement = root / "replacement.md"
            replacement.write_text("# replacement", encoding="utf-8")
            real_open = os.open
            replaced = False

            def replace_before_open(open_path, flags, *args, **kwargs):
                nonlocal replaced
                if Path(open_path) == path and not replaced:
                    replaced = True
                    replacement.replace(path)
                return real_open(open_path, flags, *args, **kwargs)

            with patch("skill2workflow.parser.os.open", side_effect=replace_before_open):
                with self.assertRaisesRegex(ValueError, "changed while being read"):
                    parse_skill_file(path)

    def test_parse_rejects_read_growth_past_bound(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("# skill", encoding="utf-8")

            with patch(
                "skill2workflow.parser.os.read",
                return_value=b"x" * (MAX_SKILL_FILE_BYTES + 1),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes",
                ):
                    parse_skill_file(path)

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
