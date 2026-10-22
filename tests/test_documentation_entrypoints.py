from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class DocumentationEntrypointTests(TestCase):
    def test_readme_is_a_short_entrypoint_not_a_delivery_history(self):
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertLessEqual(len(text.splitlines()), 300)
        summary = text.split('## Roadmap\n', 1)[1].split('\n## ', 1)[0]
        self.assertLessEqual(len(summary.split()), 100)
        self.assertNotRegex(text, r'(?m)^Loop (?:[5-9]\d|[12]\d\d) (?:adds|makes|hardens|fixes)')

    def test_task_hub_links_a_complete_reference(self):
        text = (ROOT / 'docs/README.md').read_text(encoding='utf-8')
        self.assertLessEqual(len(text.splitlines()), 180)
        self.assertIn('(reference.md)', text)
        self.assertIn('## Start here', text)
        self.assertIn('## Operate one self-hosted instance', text)
        self.assertIn('## Review, recover, and troubleshoot', text)

    def test_all_public_guides_are_reachable_and_entry_links_are_valid(self):
        from scripts.documentation_check import check_documentation
        report = check_documentation(ROOT)
        self.assertTrue(report['ok'], report['errors'])
        self.assertGreaterEqual(report['public_guides'], 100)
        self.assertLessEqual(report['max_guide_hops'], 3)

    def test_link_check_does_not_accept_missing_files_or_anchors(self):
        from scripts.documentation_check import check_links
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'README.md').write_text('[missing](gone.md)\n[section](guide.md#absent)\n')
            (root / 'guide.md').write_text('# Existing\n')
            errors = check_links(root, Path('README.md'))
            self.assertEqual({error['code'] for error in errors}, {'missing_target', 'missing_anchor'})

    def test_link_check_ignores_examples_and_external_urls_without_network(self):
        from scripts.documentation_check import check_links
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'README.md').write_text('```markdown\n[example](gone.md)\n```\n'
                                          '[web](https://example.invalid/page)\n[mail](mailto:team@example.invalid)\n')
            self.assertEqual(check_links(root, Path('README.md')), [])

    def test_anchor_rules_handle_code_unicode_punctuation_and_duplicate_headings(self):
        from scripts.documentation_check import check_links
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'README.md').write_text('[a](guide.md#use-skillmd)\n[b](guide.md#恢复-草稿)\n'
                                          '[c](guide.md#repeat-1)\n')
            (root / 'guide.md').write_text('# Use `SKILL.md`\n## 恢复 草稿\n## Repeat\n## Repeat\n', encoding='utf-8')
            self.assertEqual(check_links(root, Path('README.md')), [])

    def test_link_check_refuses_repository_escape(self):
        from scripts.documentation_check import check_links
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'README.md').write_text('[escape](../outside.md)\n')
            self.assertEqual(check_links(root, Path('README.md'))[0]['code'], 'outside_repository')

    def test_navigation_requires_a_real_bounded_path(self):
        from scripts.documentation_check import find_path
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'README.md').write_text('[hub](hub.md)\n')
            (root / 'hub.md').write_text('[guide](guide.md)\n')
            (root / 'guide.md').write_text('# Guide\n## Details\n')
            self.assertEqual(find_path(root, 'README.md', 'guide.md#details', 2), ('README.md', 'hub.md', 'guide.md'))
            self.assertIsNone(find_path(root, 'README.md', 'guide.md', 1))
            self.assertIsNone(find_path(root, 'README.md', 'guide.md#absent', 3))

    def test_reference_cannot_omit_a_guide_even_if_another_path_reaches_it(self):
        from scripts.documentation_check import check_documentation
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'docs').mkdir()
            (root / 'README.md').write_text('[hub](docs/README.md)\n[guide](docs/guide.md)\n'
                                          '## Roadmap\nCurrent status.\n')
            (root / 'docs/README.md').write_text('[reference](reference.md)\n')
            (root / 'docs/reference.md').write_text('# Reference\n')
            (root / 'docs/guide.md').write_text('# Guide\n')
            report = check_documentation(root)
            self.assertIn({'code': 'missing_reference_entry', 'source': 'docs/guide.md'}, report['errors'])

    def test_missing_entrypoints_are_reported_instead_of_crashing(self):
        from scripts.documentation_check import check_documentation
        with TemporaryDirectory() as temporary:
            report = check_documentation(Path(temporary))
            self.assertFalse(report['ok'])
            self.assertEqual(sum(error['code'] == 'missing_entrypoint' for error in report['errors']), 3)
