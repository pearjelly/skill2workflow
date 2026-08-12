import re
from pathlib import Path
from unittest import TestCase
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    ROOT / "CHANGELOG.md",
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "HARNESS.md",
    ROOT / "ROADMAP.md",
    ROOT / "GOVERNANCE.md",
    ROOT / "SECURITY.md",
    ROOT / "SUPPORT.md",
    ROOT / "CODE_OF_CONDUCT.md",
    *sorted((ROOT / "docs").glob("*.md")),
    *sorted((ROOT / "docs" / "releases").glob("*.md")),
)


class PublicDocumentationLinkTests(TestCase):
    def test_relative_links_and_images_resolve_inside_the_repository(self):
        broken = []

        for source in PUBLIC_DOCS:
            text = source.read_text(encoding="utf-8")
            for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
                raw_target = match.group(1).strip()
                if raw_target.startswith(
                    ("#", "http://", "https://", "mailto:")
                ):
                    continue
                target = raw_target.split()[0].strip("<>").split("#", 1)[0]
                if not target:
                    continue
                resolved = (source.parent / unquote(target)).resolve()
                if (
                    resolved != ROOT
                    and ROOT not in resolved.parents
                    or not resolved.exists()
                ):
                    broken.append(
                        "{path}:{line} -> {target}".format(
                            path=source.relative_to(ROOT),
                            line=text.count("\n", 0, match.start()) + 1,
                            target=raw_target,
                        )
                    )

        self.assertEqual(broken, [])
