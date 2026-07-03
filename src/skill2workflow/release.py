"""Release preflight checks for skill2workflow maintainers."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: Sequence[str]


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    message: str

    def to_dict(self):
        return {"name": self.name, "status": self.status, "message": self.message}


@dataclass(frozen=True)
class PreflightResult:
    version: str
    tag: str
    dry_run: bool
    checks: Sequence[PreflightCheck]

    @property
    def ok(self) -> bool:
        return all(check.status != "failed" for check in self.checks)

    def to_dict(self):
        return {
            "ok": self.ok,
            "version": self.version,
            "tag": self.tag,
            "dry_run": self.dry_run,
            "checks": [check.to_dict() for check in self.checks],
        }


CommandRunner = Callable[[Sequence[str], Path], CommandResult]


def run_release_preflight(
    repo_root: Path,
    *,
    version: str,
    notes: Path,
    dry_run: bool = True,
    skip_git: bool = False,
    skip_commands: bool = False,
    command_runner: Optional[CommandRunner] = None,
    verification_commands: Optional[Sequence[CommandSpec]] = None,
) -> PreflightResult:
    """Run read-only checks before a release tag is created."""

    repo_root = Path(repo_root).resolve()
    version = version.strip()
    tag = f"v{version}"
    runner = command_runner or _run_command
    checks: List[PreflightCheck] = []

    checks.append(_check_version_format(version))
    checks.append(_check_project_version(repo_root / "pyproject.toml", version))
    checks.append(_check_module_version(repo_root / "src" / "skill2workflow" / "__init__.py", version))
    checks.append(_check_release_notes(repo_root, notes, version, tag))

    if skip_git:
        checks.append(_skipped("git_status", "git checks skipped"))
        checks.append(_skipped("tag_available", "tag availability checks skipped"))
    else:
        checks.extend(_check_git_state(repo_root, tag, runner))

    if skip_commands:
        checks.append(_skipped("commands", "verification commands skipped"))
    else:
        commands = verification_commands or default_verification_commands(repo_root)
        checks.extend(_check_verification_commands(repo_root, commands, runner))

    return PreflightResult(version=version, tag=tag, dry_run=dry_run, checks=checks)


def default_verification_commands(repo_root: Path) -> Sequence[CommandSpec]:
    py_files = sorted(
        str(path.relative_to(repo_root)) for path in (repo_root / "src" / "skill2workflow").glob("*.py")
    )
    return [
        CommandSpec("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        CommandSpec("py_compile", [sys.executable, "-m", "py_compile", *py_files]),
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only release preflight checks.")
    parser.add_argument("--version", required=True, help="Package version, for example 0.1.1")
    parser.add_argument(
        "--notes",
        type=Path,
        required=True,
        help="Release notes path, for example docs/releases/v0.1.1.md",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true", help="Label this run as a dry-run. The command is read-only.")
    parser.add_argument("--skip-git", action="store_true", help="Skip clean-tree and tag availability checks.")
    parser.add_argument("--skip-commands", action="store_true", help="Skip verification command execution.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    result = run_release_preflight(
        args.repo_root,
        version=args.version,
        notes=args.notes,
        dry_run=args.dry_run,
        skip_git=args.skip_git,
        skip_commands=args.skip_commands,
    )
    if args.format == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text_result(result)
    return 0 if result.ok else 1


def _check_version_format(version: str) -> PreflightCheck:
    if version.startswith("v"):
        return _failed("version_format", "use package version format without a leading v")
    if re.fullmatch(r"\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]+)?", version):
        return _passed("version_format", f"version {version} is accepted")
    return _failed("version_format", f"version {version!r} is not semver-like")


def _check_project_version(path: Path, expected: str) -> PreflightCheck:
    return _check_version_file("project_version", path, r"(?m)^version\s*=\s*[\"']([^\"']+)[\"']", expected)


def _check_module_version(path: Path, expected: str) -> PreflightCheck:
    return _check_version_file("module_version", path, r"(?m)^__version__\s*=\s*[\"']([^\"']+)[\"']", expected)


def _check_version_file(name: str, path: Path, pattern: str, expected: str) -> PreflightCheck:
    if not path.exists():
        return _failed(name, f"{path} is missing")
    match = re.search(pattern, path.read_text(encoding="utf-8"))
    if not match:
        return _failed(name, f"{path} does not declare a version")
    actual = match.group(1)
    if actual != expected:
        return _failed(name, f"{path} has {actual}, expected {expected}")
    return _passed(name, f"{path.name} declares {expected}")


def _check_release_notes(repo_root: Path, notes: Path, version: str, tag: str) -> PreflightCheck:
    notes_path = notes if notes.is_absolute() else repo_root / notes
    if not notes_path.exists():
        return _failed("release_notes", f"{notes_path} is missing")

    problems = []
    if notes_path.name != f"{tag}.md":
        problems.append(f"filename must be {tag}.md")
    text = notes_path.read_text(encoding="utf-8")
    if tag not in text:
        problems.append(f"content must mention {tag}")
    if f"Package version: `{version}`" not in text:
        problems.append(f"content must include Package version: `{version}`")
    if problems:
        return _failed("release_notes", "; ".join(problems))
    try:
        display_path = notes_path.relative_to(repo_root)
    except ValueError:
        display_path = notes_path
    return _passed("release_notes", f"{display_path} matches {tag}")


def _check_git_state(repo_root: Path, tag: str, runner: CommandRunner) -> Sequence[PreflightCheck]:
    checks: List[PreflightCheck] = []
    status = runner(["git", "status", "--porcelain"], repo_root)
    if status.returncode != 0:
        checks.append(_failed("git_status", _command_error("git status --porcelain", status)))
    elif status.stdout.strip():
        checks.append(_failed("git_status", "working tree is not clean"))
    else:
        checks.append(_passed("git_status", "working tree is clean"))

    local_tag = runner(["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"], repo_root)
    if local_tag.returncode == 0:
        checks.append(_failed("tag_available", f"local tag {tag} already exists"))
        return checks

    remote_tag = runner(["git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{tag}"], repo_root)
    if remote_tag.returncode == 0:
        checks.append(_failed("tag_available", f"remote tag {tag} already exists"))
    elif remote_tag.returncode == 2:
        checks.append(_passed("tag_available", f"tag {tag} is available"))
    else:
        checks.append(_failed("tag_available", _command_error(f"git ls-remote origin refs/tags/{tag}", remote_tag)))
    return checks


def _check_verification_commands(
    repo_root: Path, commands: Iterable[CommandSpec], runner: CommandRunner
) -> Sequence[PreflightCheck]:
    checks = []
    for spec in commands:
        result = runner(spec.command, repo_root)
        check_name = f"command:{spec.name}"
        command_text = " ".join(spec.command)
        if result.returncode == 0:
            checks.append(_passed(check_name, f"{command_text} passed"))
        else:
            checks.append(_failed(check_name, _command_error(command_text, result)))
    return checks


def _run_command(command: Sequence[str], cwd: Path) -> CommandResult:
    env = os.environ.copy()
    src_path = str(cwd / "src")
    if (cwd / "src").exists():
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = src_path if not existing else f"{src_path}{os.pathsep}{existing}"
    completed = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True)
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _command_error(command: str, result: CommandResult) -> str:
    output = (result.stderr or result.stdout).strip()
    if output:
        return f"{command} failed with exit {result.returncode}: {output}"
    return f"{command} failed with exit {result.returncode}"


def _print_text_result(result: PreflightResult) -> None:
    overall = "PASS" if result.ok else "FAIL"
    mode = "dry-run" if result.dry_run else "read-only"
    print(f"{overall} release preflight for {result.tag} ({mode})")
    for check in result.checks:
        print(f"{check.status.upper()} {check.name}: {check.message}")


def _passed(name: str, message: str) -> PreflightCheck:
    return PreflightCheck(name, "passed", message)


def _failed(name: str, message: str) -> PreflightCheck:
    return PreflightCheck(name, "failed", message)


def _skipped(name: str, message: str) -> PreflightCheck:
    return PreflightCheck(name, "skipped", message)


if __name__ == "__main__":
    raise SystemExit(main())
