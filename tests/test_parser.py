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
        self.assertNotIn("## Checklist", ir["verification_rules"])
        self.assertNotIn("# Approval Flow Skill", ir["human_gates"])
