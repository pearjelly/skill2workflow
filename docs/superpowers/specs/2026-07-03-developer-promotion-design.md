# Developer Promotion Design

## Summary

Promote `skill2workflow` to developers and early open-source contributors as a small, runnable harness for turning Agent `SKILL.md` files into testable workflow artifacts. The developer message should favor concrete commands, inspectable examples, and clear contribution lanes over broad enterprise platform language.

## Audience

The primary audience is developers who build agent tools, workflow runtimes, internal automation platforms, or evaluation harnesses. They should be able to understand the project in one minute, clone it, run the tests, compile an example Skill, and see where a first contribution could land.

Secondary audiences are technical founders, platform engineers, and AI infrastructure maintainers who want to reason about agent governance through code rather than slideware.

## Positioning

Core tagline:

```text
Compile Agent SKILL.md files into testable, auditable workflow artifacts.
```

Developer hook:

```text
Clone it, run the tests, compile a Skill, inspect the workflow.
```

Long-form positioning:

`skill2workflow` asks what happens when Agent skills stop being only prose instructions and become workflow artifacts with validation, execution state, human gates, visualization, and audit logs. The current project is intentionally a dependency-light Python harness, not a finished enterprise platform. That makes it easier for contributors to inspect the whole loop and improve one layer at a time.

## Message Pillars

1. Runnable from a fresh checkout
   - Python 3.9+.
   - Runtime code uses the Python standard library.
   - The test suite and CLI smoke path are documented in `CONTRIBUTING.md`.

2. Real artifact pipeline
   - `SKILL.md` parses into Skill IR.
   - Skill IR compiles into Workflow DSL.
   - Workflow DSL validates, executes, visualizes, publishes, and audits.
   - LiteGraph JSON is an editor/view; Workflow DSL remains the execution truth source.

3. Contribution-friendly architecture
   - Parser coverage for real-world `SKILL.md` styles.
   - Compiler rules and workflow node types.
   - Validator and JSON Schema coverage.
   - Executor policies such as retry, timeout, and checkpoint behavior.
   - Connector manifests and connector runtime hardening.
   - LiteGraph editor UI and safe write-back fields.
   - Example workflows for real agent operating patterns.

4. Honest maturity boundary
   - The project is pre-alpha.
   - `v0.1.0` is a bootstrap release.
   - Stable `0.1.x` surfaces are documented.
   - Enterprise credential management, cloud control plane, full IAM, distributed scheduling, and complete BPMN compatibility remain out of scope.

## Promotion Assets

### GitHub Description

```text
Compile Agent SKILL.md files into testable, auditable workflow artifacts.
```

### Short English Post

```text
I am building skill2workflow, an open-source Python harness that compiles Agent SKILL.md files into controlled workflow artifacts.

The current loop is intentionally small and runnable:

SKILL.md -> Skill IR -> Workflow DSL -> local executor -> run log

It can parse skills, validate Workflow DSL, pause at human gates, resume runs, persist JSON or SQLite state, render LiteGraph-compatible graphs, publish immutable local workflow versions, and inspect audit trails.

The project is pre-alpha, but the contribution surface is already pretty tangible: parser coverage, workflow node types, validator rules, executor policies, connectors, LiteGraph write-back, and real-world example workflows.

If you are interested in agent tooling, workflow runtimes, or turning prompt-like capability docs into testable artifacts, I would love feedback and contributors.
```

### Short Chinese Post

```text
我在做一个开源项目 skill2workflow：把 Agent 的 SKILL.md 能力说明编译成可测试、可验证、可恢复、可审计的工作流工件。

当前闭环很小，但能跑：

SKILL.md -> Skill IR -> Workflow DSL -> 本地执行器 -> 运行日志

它已经支持解析 Skill、生成和校验 Workflow DSL、human gate 暂停/恢复、JSON/SQLite 状态持久化、LiteGraph 可视化、本地发布不可变 workflow version、审计日志和示例工作流。

项目还处于 pre-alpha，更像一个给开发者拆解和贡献的 harness。适合切入的地方包括 parser 覆盖、workflow node 类型、validator、executor policy、connector、LiteGraph 编辑器和真实场景 examples。

如果你对 Agent tooling、workflow runtime，或者把提示词/能力说明变成可测试工件感兴趣，欢迎试跑和提建议。
```

### README Developer Blurb

```text
Developer-first quick loop: run the tests, compile an example `SKILL.md`, validate the Workflow DSL, render a LiteGraph view, and execute the workflow locally without installing runtime dependencies.
```

### Contribution Callout

```text
Good first contribution lanes include parser coverage for real-world `SKILL.md` formats, validator rules, workflow node types, LiteGraph inspector fields, executor policies, connector fixtures, and example workflows.
```

## Channel Plan

1. GitHub repository metadata
   - Use the GitHub description as the compact tagline.
   - Keep README language concrete and command-oriented.

2. Developer social post
   - Publish the short English post with a link to the repository and one screenshot from `docs/assets/skill2workflow-editor.jpg`.
   - Use the Chinese post for Chinese developer communities.

3. Contributor routing
   - Point interested developers to `CONTRIBUTING.md`, `docs/examples.md`, and `ROADMAP.md`.
   - Emphasize small, testable contribution lanes.

## Scope

This promotion pass should create messaging assets and optionally update lightweight docs or repository copy. It should not add runtime behavior, rework product architecture, or change Workflow DSL compatibility.

The work should avoid editing unrelated in-progress connector changes unless the user explicitly asks to integrate the promotion copy into those files.

## Validation

Promotion copy is valid when:

- It accurately reflects current repository capabilities.
- It does not claim production readiness.
- It identifies `skill2workflow` as pre-alpha or bootstrap-stage where maturity matters.
- It names concrete developer entry points.
- It links messaging back to existing evidence in `README.md`, `CONTRIBUTING.md`, `docs/examples.md`, `ROADMAP.md`, and release/stability docs.

## Next Step After Spec Approval

After this design is reviewed, create a focused implementation plan for the promotion pass. The likely first implementation should add or refine developer-facing copy without touching runtime code.
