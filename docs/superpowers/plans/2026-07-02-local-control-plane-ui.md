# Local Control Plane UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local operator surface for inspecting published workflows, runs, audit events, and version comparisons without reading raw JSON files.

**Architecture:** Keep Workflow DSL and control-plane storage authoritative. Add a read-only `control-snapshot` export path backed by existing `LocalControlPlane` APIs, then add a dependency-free static inspector that loads snapshot JSON from a generated file, example file, or upload.

**Tech Stack:** Python 3.9 standard library, `unittest`, static HTML/CSS/JavaScript.

---

### Task 1: Snapshot API And CLI

**Files:**
- Create: `src/skill2workflow/dashboard.py`
- Modify: `src/skill2workflow/cli.py`
- Test: `tests/test_dashboard.py`
- Test: `tests/test_cli.py`

- [x] Write failing tests for `build_control_snapshot(state_dir, storage="json")`.
- [x] Write failing CLI test for `control-snapshot --state-dir <dir> -o <file>`.
- [x] Implement snapshot generation with `workflows`, `runs`, `audit_events`, `connectors`, `summary`, and `version_comparisons`.
- [x] Implement the CLI command.

### Task 2: Static Inspector

**Files:**
- Create: `web/control.html`
- Create: `web/control.css`
- Create: `web/control.js`
- Create: `examples/control-plane-snapshot.json`

- [x] Build a work-focused static UI with workflow registry, runs, audit timeline, connector status, and version comparison panels.
- [x] Support loading `../examples/control-plane-snapshot.json`.
- [x] Support loading a locally generated snapshot via file input.
- [x] Keep the UI read-only.

### Task 3: Documentation And Roadmap

**Files:**
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `AGENTS.md`
- Modify: `ROADMAP.md`
- Modify: `CONTRIBUTING.md`

- [x] Add `control-snapshot` command references.
- [x] Document `web/control.html` preview steps.
- [x] Mark Loop 13 complete and move the active roadmap to the next closed loop.

### Task 4: Verification And PR

**Files:**
- No additional files.

- [x] Run targeted RED/GREEN tests.
- [x] Run full test suite.
- [x] Run CLI snapshot smoke.
- [x] Run local web smoke for `web/control.html`.
- [x] Commit, push, and open a draft PR.
