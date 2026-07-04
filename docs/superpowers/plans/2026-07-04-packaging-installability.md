# Packaging And Installability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make editable installation and the `skill2workflow` console script reliable for contributors without changing runtime behavior.

**Architecture:** Keep the source-checkout workflow as the baseline and add package-level verification around the existing `pyproject.toml` console script. Use standard-library tests for metadata guards and a small maintainer smoke script for editable-install verification so normal unit tests stay deterministic and dependency-light.

**Tech Stack:** Python 3.9 standard library, `unittest`, `venv`, `pip`, existing `setuptools` packaging metadata.

---

### Task 1: Package Metadata Guardrails

**Files:**
- Create: `tests/test_packaging.py`
- Modify only if a guard fails: `pyproject.toml`

- [x] **Step 1: Write metadata tests**

Add `tests/test_packaging.py` with tests that read `pyproject.toml` as text and assert the package contract that matters for installability:

```python
from pathlib import Path
from unittest import TestCase


class PackagingMetadataTests(TestCase):
    def test_pyproject_declares_expected_package_metadata(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")

        self.assertIn('name = "skill2workflow"', text)
        self.assertIn('version = "0.1.0"', text)
        self.assertIn('readme = "README.md"', text)
        self.assertIn('requires-python = ">=3.9"', text)
        self.assertIn('license = { text = "Apache-2.0" }', text)
        self.assertIn('skill2workflow = "skill2workflow.cli:main"', text)

    def test_pyproject_keeps_runtime_dependencies_empty(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")

        self.assertNotIn("[project.dependencies]", text)
        self.assertNotIn("dependencies = [", text)
```

- [x] **Step 2: Run focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_packaging -v
```

Expected: pass against the current package metadata unless the metadata has drifted.

### Task 2: Editable Install Smoke Script

**Files:**
- Create: `scripts/package_smoke.py`

- [x] **Step 1: Add a checkout-local smoke helper**

Create `scripts/package_smoke.py` that:

- creates a temporary virtual environment under `--work-dir`
- installs the repository with `python -m pip install --no-build-isolation -e .`
- verifies package metadata with `importlib.metadata`
- runs `skill2workflow --help`
- runs `skill2workflow validate examples/workflows/approval-flow.workflow.json --format json`

- [x] **Step 2: Run the smoke helper**

Run:

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```

Expected: exit `0` and print a JSON summary containing the virtual environment path, package version, console script path, and validation command status.

### Task 3: Contributor Command Alignment

**Files:**
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `CONTRIBUTING.md`
- Modify: `AGENTS.md`

- [x] **Step 1: Document editable install**

Add the install path:

```bash
python3 -m venv /tmp/skill2workflow-venv
/tmp/skill2workflow-venv/bin/python -m pip install --upgrade pip "setuptools>=68"
/tmp/skill2workflow-venv/bin/python -m pip install --no-build-isolation -e .
/tmp/skill2workflow-venv/bin/skill2workflow --help
```

- [x] **Step 2: Keep source-checkout commands**

Keep `PYTHONPATH=src python3 -m skill2workflow.cli ...` commands documented as the no-install path, and present the console script as the contributor install path.

- [x] **Step 3: Document package smoke verification**

Add:

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```

### Task 4: Roadmap And Verification

**Files:**
- Modify: `ROADMAP.md`

- [x] **Step 1: Mark Loop 20 complete only after implementation**

Do not move Loop 20 to completed loops until package metadata guards, editable install smoke, and docs are merged.

- [x] **Step 2: Run final verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop20
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
git diff --check
```

Expected: all pass.
