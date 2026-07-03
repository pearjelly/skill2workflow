# Developer Promotion Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add developer-focused promotion assets that make `skill2workflow` easier to discover, understand, try, and contribute to.

**Architecture:** Keep this docs-only. Add one reusable promotion asset page under `docs/promotion/`, then add small entry-point copy to `README.md` and `CONTRIBUTING.md` that routes developers toward the runnable CLI loop and contribution lanes. Do not touch runtime code, schemas, examples, or Workflow DSL compatibility.

**Tech Stack:** Markdown documentation, existing Python CLI commands for evidence, Git diff verification.

---

## File Structure

- Create `docs/promotion/developer-announcement.md`
  - Holds copy-paste-ready English and Chinese developer posts, GitHub description, tagline variants, screenshot guidance, and repository links.
- Modify `README.md`
  - Adds a short developer-first quick loop near the top, before the existing visual overview and long capability list.
- Modify `CONTRIBUTING.md`
  - Adds a lightweight "Start Here" paragraph for developers arriving from promotion channels and sharpens the contribution lane framing.
- No tests or runtime files should be modified.

## Task 1: Create Reusable Developer Promotion Copy

**Files:**
- Create: `docs/promotion/developer-announcement.md`

- [ ] **Step 1: Create the promotion docs directory**

Run:

```bash
mkdir -p docs/promotion
```

Expected: `docs/promotion/` exists.

- [ ] **Step 2: Add the developer announcement asset page**

Create `docs/promotion/developer-announcement.md` with exactly this content:

````markdown
# Developer Announcement

This page contains copy-paste-ready developer promotion assets for `skill2workflow`.

## Repository Description

```text
Compile Agent SKILL.md files into testable, auditable workflow artifacts.
```

## Tagline Options

```text
From Agent Skills to testable workflow artifacts.
```

```text
Turn SKILL.md capability docs into runnable workflow harnesses.
```

```text
Clone it, run the tests, compile a Skill, inspect the workflow.
```

## Short English Post

```text
I am building skill2workflow, an open-source Python harness that compiles Agent SKILL.md files into controlled workflow artifacts.

The current loop is intentionally small and runnable:

SKILL.md -> Skill IR -> Workflow DSL -> local executor -> run log

It can parse skills, validate Workflow DSL, pause at human gates, resume runs, persist JSON or SQLite state, render LiteGraph-compatible graphs, publish immutable local workflow versions, and inspect audit trails.

The project is pre-alpha, but the contribution surface is already concrete: parser coverage, workflow node types, validator rules, executor policies, connectors, LiteGraph write-back, and real-world example workflows.

If you are interested in agent tooling, workflow runtimes, or turning prompt-like capability docs into testable artifacts, feedback and contributors are welcome.
```

## Short Chinese Post

```text
我在做一个开源项目 skill2workflow：把 Agent 的 SKILL.md 能力说明编译成可测试、可验证、可恢复、可审计的工作流工件。

当前闭环很小，但能跑：

SKILL.md -> Skill IR -> Workflow DSL -> 本地执行器 -> 运行日志

它已经支持解析 Skill、生成和校验 Workflow DSL、human gate 暂停/恢复、JSON/SQLite 状态持久化、LiteGraph 可视化、本地发布不可变 workflow version、审计日志和示例工作流。

项目还处于 pre-alpha，更像一个给开发者拆解和贡献的 harness。适合切入的地方包括 parser 覆盖、workflow node 类型、validator、executor policy、connector、LiteGraph 编辑器和真实场景 examples。

如果你对 Agent tooling、workflow runtime，或者把提示词/能力说明变成可测试工件感兴趣，欢迎试跑和提建议。
```

## Suggested Links

- Repository: `https://github.com/pearjelly/skill2workflow`
- Contributor guide: `CONTRIBUTING.md`
- Example workflows: `docs/examples.md`
- Roadmap: `ROADMAP.md`
- Stability boundaries: `docs/stability.md`

## Suggested Visual

Use `docs/assets/skill2workflow-editor.jpg` for developer channels because it shows the LiteGraph-compatible workflow editor and HTTP connector inspector. Use `docs/assets/skill2workflow-system-design.svg` for architecture-oriented posts.

## Copy Boundaries

- Say the project is pre-alpha or bootstrap-stage when maturity matters.
- Say Workflow DSL is the execution truth source.
- Say LiteGraph is an editor/view, not the runtime authority.
- Do not claim hosted control plane, RBAC, IAM, distributed scheduling, enterprise credential management, or production readiness.
````

- [ ] **Step 3: Inspect the new page**

Run:

```bash
sed -n '1,220p' docs/promotion/developer-announcement.md
```

Expected: The page contains repository description, tagline options, English post, Chinese post, suggested links, suggested visual, and copy boundaries.

- [ ] **Step 4: Commit Task 1**

Run:

```bash
git add docs/promotion/developer-announcement.md
git commit -m "docs: add developer promotion copy"
```

Expected: Commit succeeds with only `docs/promotion/developer-announcement.md`.

## Task 2: Add Developer Quick Loop To README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Insert developer quick loop after the first pipeline code block**

In `README.md`, find this existing block:

````markdown
```text
SKILL.md -> Skill IR -> Workflow DSL -> Local Executor -> Run Log
```

LiteGraph visualization, enterprise control plane features, and connector expansion are part of the staged roadmap in the approved spec.
````

Replace it with:

````markdown
```text
SKILL.md -> Skill IR -> Workflow DSL -> Local Executor -> Run Log
```

For developers, the quickest loop is:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json
```

No runtime dependency install is required for the current harness. Runtime code uses the Python standard library, and contribution lanes are documented in `CONTRIBUTING.md`.

LiteGraph visualization, enterprise control plane features, and connector expansion are part of the staged roadmap in the approved spec.
````

- [ ] **Step 2: Inspect the README opening**

Run:

```bash
sed -n '1,80p' README.md
```

Expected: The README now shows the developer quick loop before `## Visual Overview`.

- [ ] **Step 3: Commit Task 2**

Run:

```bash
git add README.md
git commit -m "docs: add developer quick loop"
```

Expected: Commit succeeds with only `README.md`.

## Task 3: Sharpen Contributor Routing

**Files:**
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Add a developer start paragraph**

In `CONTRIBUTING.md`, find:

```markdown
Thank you for helping improve `skill2workflow`. The project is still pre-alpha, so the most valuable contributions are small, runnable, and easy to verify.
```

Replace it with:

```markdown
Thank you for helping improve `skill2workflow`. The project is still pre-alpha, so the most valuable contributions are small, runnable, and easy to verify.

If you arrived from a developer post, start by running the fresh-checkout CLI smoke below. Then pick a contribution lane that ends in a focused test, fixture, or documentation artifact.
```

- [ ] **Step 2: Refine the contribution lane lead-in**

In `CONTRIBUTING.md`, find:

```markdown
Good first contribution lanes:
```

Replace it with:

```markdown
Good first contribution lanes for developers:
```

- [ ] **Step 3: Inspect the contributor opening and lanes**

Run:

```bash
sed -n '1,95p' CONTRIBUTING.md
```

Expected: The opening includes the developer start paragraph, and the contribution lane heading says "Good first contribution lanes for developers:".

- [ ] **Step 4: Commit Task 3**

Run:

```bash
git add CONTRIBUTING.md
git commit -m "docs: clarify developer contribution entry"
```

Expected: Commit succeeds with only `CONTRIBUTING.md`.

## Task 4: Verify Promotion Copy

**Files:**
- Inspect: `docs/promotion/developer-announcement.md`
- Inspect: `README.md`
- Inspect: `CONTRIBUTING.md`

- [ ] **Step 1: Check promotion phrases exist**

Run:

```bash
rg -n "Compile Agent SKILL.md files into testable, auditable workflow artifacts|Clone it, run the tests, compile a Skill|Good first contribution lanes for developers|No runtime dependency install" docs/promotion/developer-announcement.md README.md CONTRIBUTING.md
```

Expected: Matches appear in the promotion page, README, and CONTRIBUTING.

- [ ] **Step 2: Check maturity boundaries exist**

Run:

```bash
rg -n "pre-alpha|bootstrap-stage|not the runtime authority|Do not claim hosted control plane" docs/promotion/developer-announcement.md CONTRIBUTING.md
```

Expected: The promotion page and contributor guide include maturity and boundary language.

- [ ] **Step 3: Run whitespace verification**

Run:

```bash
git diff --check
```

Expected: No output and exit code 0.

- [ ] **Step 4: Review final commit history**

Run:

```bash
git log --oneline -n 4
```

Expected: The latest commits include developer promotion design, developer promotion copy, README developer quick loop, and developer contribution entry.

## Out Of Scope

- Do not change runtime code.
- Do not change Workflow DSL, JSON Schema, examples, or tests.
- Do not publish to external social channels from this repository task.
- Do not edit GitHub repository metadata through API calls; the GitHub description text is prepared for a human to paste.
