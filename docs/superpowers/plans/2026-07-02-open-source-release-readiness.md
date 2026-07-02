# Open Source Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare `skill2workflow` for its first open-source evaluation loop.

**Architecture:** This loop is documentation and repository-hygiene focused. It does not change runtime behavior; it adds contributor entry points, issue intake templates, release notes, and explicit compatibility boundaries around Workflow DSL `0.1.0`.

**Tech Stack:** Markdown, GitHub issue forms, Python 3.9 standard-library verification.

---

### Task 1: Contributor Entry Point

**Files:**
- Create: `CONTRIBUTING.md`
- Modify: `README.md`

- [ ] Add the exact local setup, verification, CLI smoke, web preview, and PR expectations that a new contributor needs.
- [ ] Link the guide from `README.md`.
- [ ] Verify with `git diff --check`.

### Task 2: GitHub Issue Intake

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/ISSUE_TEMPLATE/workflow_example.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`

- [ ] Add structured forms for bugs, feature requests, and real-world workflow examples.
- [ ] Keep the forms aligned with the project lanes in `ROADMAP.md`.
- [ ] Verify the YAML is plain text and does not contain placeholders.

### Task 3: Release And Compatibility Docs

**Files:**
- Create: `docs/releases/v0.1.0.md`
- Create: `docs/workflow-dsl-compatibility.md`
- Create: `docs/stability.md`
- Modify: `docs/workflow-dsl-contract.md`

- [ ] Document the first release scope and verification commands.
- [ ] Document Workflow DSL `0.1.0` compatibility commitments.
- [ ] Mark stable versus experimental surfaces for contributors and early adopters.
- [ ] Cross-link the compatibility policy from the DSL contract.

### Task 4: Roadmap And Harness Update

**Files:**
- Modify: `ROADMAP.md`
- Modify: `HARNESS.md`
- Modify: `AGENTS.md`

- [ ] Mark Loop 12 as complete in the roadmap.
- [ ] Move the active roadmap to Loop 13 Local Control Plane UI.
- [ ] Add the new docs to local agent and harness references.

### Task 5: Verification And PR

**Files:**
- No additional files.

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [ ] Run `python3 -m py_compile src/skill2workflow/*.py`.
- [ ] Run `git diff --check`.
- [ ] Commit, push, and open a PR for Loop 12.
