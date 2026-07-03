# Release Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only release preflight path that makes future `0.1.x` releases repeatable before any GitHub tag or release is created.

**Architecture:** The preflight logic lives in a small standard-library Python module so tests can call it directly. A thin script exposes the maintainer command path, while GitHub Actions runs the same script in dry-run mode on pull requests.

**Tech Stack:** Python 3.9 standard library, unittest, GitHub Actions, Markdown.

---

### Task 1: Release Preflight Tests

**Files:**
- Create: `tests/test_release_preflight.py`

- [x] Add tests for matching versions, version mismatches, missing release notes, existing tags, dirty working trees, and command execution.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.test_release_preflight -v` and confirm RED before implementation.

### Task 2: Release Preflight Module And Script

**Files:**
- Create: `src/skill2workflow/release.py`
- Create: `scripts/release_preflight.py`

- [x] Implement `run_release_preflight()` with read-only checks for requested version, release notes, tag availability, working tree cleanliness, and verification commands.
- [x] Expose a script entry point that accepts `--version`, `--notes`, `--dry-run`, `--skip-git`, and `--skip-commands`.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.test_release_preflight -v` and confirm GREEN.

### Task 3: Release Docs And CI Dry-Run

**Files:**
- Create: `docs/release-process.md`
- Create: `.github/workflows/release-preflight.yml`
- Modify: `ROADMAP.md`

- [x] Document the maintainer preflight path, release PR evidence, and manual fallback used for `v0.1.0`.
- [x] Add a GitHub Actions dry-run workflow that exercises release preflight without creating tags or releases.
- [x] Mark Loop 15 as complete and move the near-term queue to Loop 16.

### Task 4: Verification And PR

**Files:**
- No additional files.

- [x] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [x] Run `python3 -m py_compile src/skill2workflow/*.py`.
- [x] Run `PYTHONPATH=src python3 scripts/release_preflight.py --version 0.1.1 --notes docs/releases/v0.1.0.md --dry-run --skip-git --skip-commands` and confirm the known mismatch fails.
- [x] Run `git diff --check`.
- [x] Commit, push, and open a draft PR for Loop 15.
