# Workflow Example Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add enterprise workflow examples that prove `skill2workflow` can turn realistic Agent skills into inspectable Workflow DSL and LiteGraph fixtures.

**Architecture:** Each scenario starts from `examples/skills/<scenario>/SKILL.md`. The committed Workflow DSL and LiteGraph files are generated artifacts that must stay synchronized with the source skill through tests and CLI verification.

**Tech Stack:** Python 3.9 standard library, unittest, existing `skill2workflow` CLI, Markdown, static LiteGraph web gallery.

---

### Task 1: Example Synchronization Test

**Files:**
- Create: `tests/test_examples.py`

- [x] Add a test that compiles each `examples/skills/*/SKILL.md` and compares it with `examples/workflows/<scenario>.workflow.json`.
- [x] Add a test that renders each committed Workflow DSL fixture and compares it with `examples/workflows/<scenario>.litegraph.json`.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.test_examples -v` and confirm RED before adding new scenario fixtures.

### Task 2: Enterprise Scenario Skills

**Files:**
- Create: `examples/skills/sales-follow-up/SKILL.md`
- Create: `examples/skills/customer-service-escalation/SKILL.md`
- Create: `examples/skills/risk-review/SKILL.md`
- Create: `examples/skills/operations-analysis/SKILL.md`

- [x] Add realistic checklists with required order, hard gates, human approvals, tool boundaries, and verification steps.
- [x] Keep the examples dependency-free and local-first.

### Task 3: Generated Workflow Fixtures

**Files:**
- Create: `examples/workflows/sales-follow-up.workflow.json`
- Create: `examples/workflows/customer-service-escalation.workflow.json`
- Create: `examples/workflows/risk-review.workflow.json`
- Create: `examples/workflows/operations-analysis.workflow.json`
- Create: matching `.litegraph.json` fixtures for each scenario.

- [x] Generate each Workflow DSL fixture with `PYTHONPATH=src python3 -m skill2workflow.cli compile`.
- [x] Validate each Workflow DSL fixture with `PYTHONPATH=src python3 -m skill2workflow.cli validate --format json`.
- [x] Generate each LiteGraph fixture with `PYTHONPATH=src python3 -m skill2workflow.cli visualize`.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.test_examples -v` and confirm GREEN.

### Task 4: Docs And Gallery

**Files:**
- Create: `docs/examples.md`
- Modify: `docs/authoring.md`
- Modify: `README.md`
- Modify: `web/index.html`
- Modify: `web/app.js`

- [x] Document each scenario, control pattern, and inspection command.
- [x] Add examples to the LiteGraph gallery select list and loader map.
- [x] Link the example pack from README and authoring docs.

### Task 5: Verification And PR

**Files:**
- No additional files.

- [x] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [x] Run `python3 -m py_compile src/skill2workflow/*.py`.
- [x] Run compile, validate, and visualize commands for all new scenarios.
- [x] Run `git diff --check`.
- [x] Commit, push, and open a draft PR for Loop 16.
