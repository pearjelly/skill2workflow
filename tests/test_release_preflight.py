from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.release import CommandResult, CommandSpec, run_release_preflight


class ReleasePreflightTests(TestCase):
    def test_preflight_passes_when_versions_notes_git_and_commands_agree(self):
        with TemporaryDirectory() as tmp:
            repo_root = _write_release_repo(Path(tmp), version="0.1.1")
            runner = FakeRunner(
                {
                    ("git", "status", "--porcelain"): CommandResult(0, "", ""),
                    ("git", "rev-parse", "--verify", "--quiet", "refs/tags/v0.1.1"): CommandResult(1, "", ""),
                    ("git", "ls-remote", "--exit-code", "--tags", "origin", "refs/tags/v0.1.1"): CommandResult(
                        2, "", ""
                    ),
                    ("python", "-m", "unittest"): CommandResult(0, "tests ok", ""),
                }
            )

            result = run_release_preflight(
                repo_root,
                version="0.1.1",
                notes=Path("docs/releases/v0.1.1.md"),
                command_runner=runner,
                verification_commands=[CommandSpec("unit_tests", ["python", "-m", "unittest"])],
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.tag, "v0.1.1")
        self.assertEqual(runner.commands[-1], ("python", "-m", "unittest"))

    def test_preflight_rejects_package_version_mismatch(self):
        with TemporaryDirectory() as tmp:
            repo_root = _write_release_repo(Path(tmp), version="0.1.0", init_version="0.1.1")

            result = run_release_preflight(
                repo_root,
                version="0.1.0",
                notes=Path("docs/releases/v0.1.0.md"),
                skip_git=True,
                skip_commands=True,
            )

        self.assertFalse(result.ok)
        self.assertIn("module_version", _failed_check_names(result))

    def test_preflight_rejects_release_notes_that_do_not_match_requested_version(self):
        with TemporaryDirectory() as tmp:
            repo_root = _write_release_repo(Path(tmp), version="0.1.1")
            (repo_root / "docs" / "releases" / "v0.1.0.md").write_text(
                "# skill2workflow v0.1.0 Release Notes\n\n- Package version: `0.1.0`\n",
                encoding="utf-8",
            )

            result = run_release_preflight(
                repo_root,
                version="0.1.1",
                notes=Path("docs/releases/v0.1.0.md"),
                skip_git=True,
                skip_commands=True,
            )

        self.assertFalse(result.ok)
        self.assertIn("release_notes", _failed_check_names(result))

    def test_preflight_rejects_missing_release_notes(self):
        with TemporaryDirectory() as tmp:
            repo_root = _write_release_repo(Path(tmp), version="0.1.1")

            result = run_release_preflight(
                repo_root,
                version="0.1.1",
                notes=Path("docs/releases/v0.1.1-missing.md"),
                skip_git=True,
                skip_commands=True,
            )

        self.assertFalse(result.ok)
        self.assertIn("release_notes", _failed_check_names(result))

    def test_preflight_rejects_dirty_working_tree(self):
        with TemporaryDirectory() as tmp:
            repo_root = _write_release_repo(Path(tmp), version="0.1.1")
            runner = FakeRunner({("git", "status", "--porcelain"): CommandResult(0, " M ROADMAP.md\n", "")})

            result = run_release_preflight(
                repo_root,
                version="0.1.1",
                notes=Path("docs/releases/v0.1.1.md"),
                command_runner=runner,
                skip_commands=True,
            )

        self.assertFalse(result.ok)
        self.assertIn("git_status", _failed_check_names(result))

    def test_preflight_rejects_existing_local_tag(self):
        with TemporaryDirectory() as tmp:
            repo_root = _write_release_repo(Path(tmp), version="0.1.1")
            runner = FakeRunner(
                {
                    ("git", "status", "--porcelain"): CommandResult(0, "", ""),
                    ("git", "rev-parse", "--verify", "--quiet", "refs/tags/v0.1.1"): CommandResult(0, "v0.1.1", ""),
                }
            )

            result = run_release_preflight(
                repo_root,
                version="0.1.1",
                notes=Path("docs/releases/v0.1.1.md"),
                command_runner=runner,
                skip_commands=True,
            )

        self.assertFalse(result.ok)
        self.assertIn("tag_available", _failed_check_names(result))

    def test_preflight_rejects_failed_verification_command(self):
        with TemporaryDirectory() as tmp:
            repo_root = _write_release_repo(Path(tmp), version="0.1.1")
            runner = FakeRunner(
                {
                    ("python", "-m", "unittest"): CommandResult(1, "", "failed"),
                }
            )

            result = run_release_preflight(
                repo_root,
                version="0.1.1",
                notes=Path("docs/releases/v0.1.1.md"),
                command_runner=runner,
                skip_git=True,
                verification_commands=[CommandSpec("unit_tests", ["python", "-m", "unittest"])],
            )

        self.assertFalse(result.ok)
        self.assertIn("command:unit_tests", _failed_check_names(result))


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.commands = []

    def __call__(self, command, cwd):
        key = tuple(command)
        self.commands.append(key)
        return self.responses.get(key, CommandResult(0, "", ""))


def _write_release_repo(root: Path, version: str, init_version: str = "") -> Path:
    package_dir = root / "src" / "skill2workflow"
    release_dir = root / "docs" / "releases"
    package_dir.mkdir(parents=True)
    release_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "skill2workflow"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        f'"""test package."""\n\n__version__ = "{init_version or version}"\n',
        encoding="utf-8",
    )
    (release_dir / f"v{version}.md").write_text(
        f"# skill2workflow v{version} Release Notes\n\n- Package version: `{version}`\n",
        encoding="utf-8",
    )
    return root


def _failed_check_names(result):
    return [check.name for check in result.checks if check.status == "failed"]
