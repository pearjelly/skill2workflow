# skill2workflow 正式设计方案

日期：2026-07-01

## 1. 产品愿景

`skill2workflow` 是一个面向企业 AI 落地的开源 Agent Workflow Runtime。它把已经被验证有效的 Agent `Skill` 能力描述，转换为高可控、可视化、可执行、可恢复、可审计的企业级 workflow。

项目的核心主张是：

> From Agent Skills to Controlled Enterprise Workflows.

当前基于智能体 Skill 的 AI 能力落地已经证明了效率和适应性：它能快速描述“Agent 会做什么”，并通过工具调用、上下文说明和操作规范提升通用 Agent 的能力边界。但企业核心业务流程更看重“高可控”：流程必须按规则执行，关键节点必须审批，执行状态必须可追踪，失败后必须可恢复，产出必须稳定一致。

`skill2workflow` 解决的是企业 AI 应用落地的最后一步：把“能力层”的 Skill，编译成“执行控制层”的 Workflow。

## 2. 背景与问题

### 2.1 Skill 的价值

Skill 适合表达 Agent 的能力、工具使用方式、上下文规则和执行建议。它让通用 Agent 能快速适配新任务，例如报告生成、资料查询、会议总结、代码辅助、销售资料整理等。

Skill 的优势是：

- 编写成本低。
- 易于复用和分发。
- 适合快速适配不同场景。
- 与现有 Agent 生态兼容。
- 能提升通用 Agent 的任务完成效率。

### 2.2 企业场景中的缺口

企业核心流程不仅要求 Agent “会做”，还要求 Agent “必须按规则做完”。仅靠 Skill 很难满足这些要求。

典型问题包括：

- Skill 只能建议流程步骤，无法强制顺序执行。
- Agent 可能跳过步骤、误解步骤或重复步骤。
- 长流程中状态容易丢失。
- 人工审批点缺少强约束。
- 工具调用结果缺少可追踪记录。
- 失败后难以恢复到准确节点。
- 不同运行之间结果一致性难以保证。
- 企业无法对发布、权限、审计和回滚进行治理。

这使得 Skill 更像“说明书”，而不是“受控运行时”。

### 2.3 产品机会

企业 AI 落地需要一个承接层：

- 上游兼容已有 Skill 生态。
- 中间生成强约束 Workflow DSL。
- 下游提供可视化、执行、状态、审计和治理能力。

`skill2workflow` 不是另一个 Agent 框架，也不是单纯的流程图工具。它是把 Skill 转化为企业可控 workflow 的开源基础设施。

## 3. 目标与非目标

### 3.1 目标

第一阶段目标：

- 输入标准 `SKILL.md`。
- 解析为结构化 `Skill IR`。
- 编译为强约束 `Workflow DSL`。
- 使用 LiteGraph 提供类似 ComfyUI 的节点可视化。
- 使用本地 Durable Executor 强制执行 workflow。
- 保存运行状态、节点输出、失败原因和审计日志。
- 形成完整小闭环：`SKILL.md -> Skill IR -> Workflow DSL -> LiteGraph View -> Executor Run -> Run Log`。

长期目标：

- 成为企业 AI workflow 的开放运行时。
- 支持更多 Skill 标准和企业 SOP 输入。
- 支持多种执行后端、连接器和部署形态。
- 建立围绕 parser、compiler、node、connector、executor 的开源插件生态。
- 支撑销售、风控、审批、客户服务、经营分析等企业核心流程。

### 3.2 非目标

第一阶段不追求：

- 替代现有 LLM Agent 框架。
- 实现完整 BPMN 引擎。
- 实现完整企业 IAM / RBAC 系统。
- 实现云端多租户平台。
- 支持所有非标准 SOP 文档。
- 做复杂拖拽式低代码平台。
- 保证任意 Skill 都能无人工校正地生成完美 workflow。

第一阶段要证明的是：标准 Skill 可以被转换成有状态、有顺序、有检查、有暂停、有恢复能力的可执行 workflow。

## 4. 用户与场景

### 4.1 目标用户

主要用户包括：

- AI 应用开发者：希望把 Agent Skill 产品化、流程化、可运维化。
- 企业 IT / 数字化团队：需要把 AI 接入现有业务流程，并满足治理要求。
- 业务流程负责人：关心流程是否按规则执行、是否可追踪、是否可复盘。
- 开源开发者：希望贡献 parser、node、connector、executor 和 UI 扩展。
- Agent 平台厂商：希望把已有 Skill 能力转成更可靠的 workflow runtime。

### 4.2 典型场景

轻量任务适合直接使用通用 Agent 和 Skill：

- 报告生成。
- 资料查询。
- 文档总结。
- 一次性分析。
- 低风险内部辅助。

核心流程适合使用 `skill2workflow`：

- 销售跟进：线索识别、状态判断、CRM 更新、待办提醒、记录检查。
- 风控审核：数据采集、规则判断、人工复核、结果归档。
- 审批流：材料检查、审批人确认、节点流转、超时提醒。
- 客户服务：工单分级、知识库检索、回复生成、人工升级。
- 经营分析：数据拉取、指标校验、异常解释、报告发布。

## 5. 核心概念

### 5.1 Skill

Skill 是输入材料，通常以 `SKILL.md` 形式存在。它描述 Agent 的能力、触发条件、规则、工具、流程和检查要求。

### 5.2 Skill IR

Skill IR 是 Parser 输出的中间表示。它表达“从 Skill 里读出了什么”，不直接承担执行语义。

Skill IR 包含：

- 元信息。
- 触发规则。
- 硬性门禁。
- 有序步骤。
- 检查清单。
- 工具要求。
- 人工确认点。
- 验证规则。
- 输出要求。

### 5.3 Workflow DSL

Workflow DSL 是执行真相源。它表达“应该如何严格执行”。

DSL 包含：

- 节点。
- 边。
- 入口。
- 出口。
- 状态 schema。
- guard。
- checkpoint。
- failure policy。
- human gate。
- tool binding。
- version metadata。

### 5.4 Graph View

Graph View 是 workflow 的可视化表示。第一版使用 LiteGraph 实现类似 ComfyUI 的节点画布。

Graph View 不是执行真相源。保存图变更后，必须同步回 DSL，并通过 Compiler / Validator 校验。

### 5.5 Run State

Run State 表示某一次 workflow 执行实例的状态。

Run State 包含：

- `run_id`。
- workflow 版本。
- 当前节点。
- 执行上下文。
- 节点输入输出。
- 决策记录。
- 错误记录。
- 重试次数。
- human gate 等待状态。
- checkpoint 信息。

### 5.6 Control Plane

Control Plane 是企业治理层。它管理 workflow 的版本、发布、运行、审计、权限、连接器和监控。

第一版只实现最小控制面：版本号、草稿/发布状态、运行列表、运行详情、审计日志。

## 6. 设计原则

### 6.1 Standard-first

优先兼容已有 Skill 标准和生态，不重新发明 prompt 标准。项目的价值在于把 Skill 编译成强控制 workflow。

### 6.2 Runtime-first

可视化是重要体验，但不是核心壁垒。真正的企业价值来自强执行、状态持久化、失败恢复、人工门禁和审计追踪。

### 6.3 DSL as Source of Execution Truth

LiteGraph 负责展示和编辑，Workflow DSL 负责执行语义。运行器只能基于 DSL 执行，不能直接基于画布数据执行。

### 6.4 Compile Before Run

workflow 在运行前必须经过编译校验。不能让有缺失入口、孤立节点、未处理分支或缺少失败策略的 workflow 进入发布态。

### 6.5 Durable by Default

任何长流程都必须默认保存状态。执行中断、工具失败、人工等待和系统重启后，必须能恢复到明确节点。

### 6.6 Open Core of Trust

核心 parser、compiler、DSL、executor 和本地 UI 必须开源。企业用户要能审计控制逻辑，开发者要能扩展节点和连接器。

## 7. 五层架构

### 7.1 Skill Ingestion / Parser

Parser 负责读取标准 `SKILL.md` 并生成 `Skill IR`。

职责：

- 解析 frontmatter。
- 提取 `name`、`description`。
- 识别触发条件。
- 识别硬性门禁。
- 提取流程步骤。
- 提取 checklist。
- 提取工具依赖。
- 提取人工确认点。
- 提取验证规则。
- 提取输出要求。

Parser 不负责：

- 运行 workflow。
- 做业务决策。
- 直接生成 LiteGraph 画布。
- 执行工具调用。

### 7.2 DSL Compiler / Validator

Compiler 把 `Skill IR` 转成 `Workflow DSL`。Validator 保证 DSL 可执行、可发布。

职责：

- 生成节点和边。
- 生成入口和出口。
- 生成顺序执行关系。
- 生成 guard、precondition、postcondition。
- 生成 checkpoint。
- 生成 human gate。
- 生成失败路径。
- 生成默认 retry / timeout 策略。
- 校验 workflow 完整性。

基础校验规则：

- 必须有且只有一个入口节点。
- 必须至少有一个结束节点。
- 所有节点必须可从入口到达。
- 所有非结束节点必须有成功路径。
- decision 节点必须定义分支。
- human gate 必须定义恢复条件。
- tool_call 节点必须定义工具绑定。
- checkpoint 节点必须定义保存内容。
- published workflow 不能包含校验错误。

### 7.3 LiteGraph Editor

Editor 使用 LiteGraph 提供类似 ComfyUI 的可视化体验。

职责：

- 从 DSL 渲染节点图。
- 展示节点输入、输出和连线。
- 支持节点拖拽、连线和参数编辑。
- 展示编译错误和运行状态。
- 保存图变更并同步回 DSL。
- 触发重新校验。

设计约束：

- LiteGraph 图不是执行真相源。
- 图变更必须经过 DSL 校验。
- 不允许保存会破坏执行语义的图。
- UI 可以展示草稿状态，但发布必须通过 Validator。

### 7.4 Durable Executor

Executor 是企业稳定性的核心，负责按照 DSL 强制执行 workflow。

职责：

- 创建 run。
- 按节点和边执行。
- 禁止跳步骤。
- 保存 run state。
- 保存节点输入输出。
- 执行 checkpoint。
- 处理 retry、timeout、fallback。
- 在 human gate 暂停。
- 在人工确认后恢复。
- 调用工具节点。
- 记录失败和审计日志。

Executor 状态机：

- `created`：run 已创建。
- `running`：正在执行。
- `waiting`：等待人工或外部事件。
- `failed`：执行失败且无法自动恢复。
- `completed`：执行完成。
- `cancelled`：被人工取消。

### 7.5 Enterprise Control Plane

Control Plane 负责企业级治理。

第一版职责：

- workflow 版本号。
- draft / published / deprecated 状态。
- run 列表。
- run 详情。
- audit log。
- connector registry 占位。

长期职责：

- RBAC 权限。
- 发布审批。
- 环境隔离。
- 连接器凭据管理。
- 运行监控。
- 指标看板。
- SLA 和告警。
- 回滚。
- 多租户。

## 8. 数据流

完整数据流如下：

```text
SKILL.md
  -> Skill Parser
  -> Skill IR
  -> DSL Compiler
  -> Workflow DSL Draft
  -> LiteGraph Editor
  -> DSL Validator
  -> Published Workflow Version
  -> Durable Executor
  -> Run State / Audit Log / Metrics
```

关键约束：

- Parser 输出 IR，不直接运行。
- Compiler 输出 DSL，不直接渲染 UI。
- LiteGraph 编辑 DSL 的可视化投影。
- Executor 只执行已校验 DSL。
- Control Plane 管理版本和运行治理。

## 9. Workflow DSL 设计

### 9.1 顶层结构

```json
{
  "schema_version": "0.1.0",
  "workflow": {
    "id": "workflow_using_superpowers",
    "name": "using-superpowers",
    "description": "Use skills before responding or acting.",
    "version": "0.1.0",
    "status": "draft"
  },
  "entry": "start",
  "nodes": [],
  "edges": [],
  "state_schema": {},
  "guards": [],
  "checkpoints": [],
  "policies": {
    "default_retry": {
      "max_attempts": 0
    },
    "default_timeout_ms": 300000
  }
}
```

### 9.2 节点结构

```json
{
  "id": "node_explore_context",
  "type": "step",
  "title": "Explore project context",
  "description": "Check files, docs, and recent commits before implementation.",
  "requires": [],
  "produces": ["project_context"],
  "guard": null,
  "action": {
    "kind": "agent_instruction",
    "instruction": "Explore project context before proposing changes."
  },
  "on_success": "node_ask_questions",
  "on_failure": "node_failure",
  "retry": {
    "max_attempts": 0
  },
  "metadata": {
    "source": {
      "file": "SKILL.md",
      "section": "Checklist"
    }
  }
}
```

### 9.3 节点类型

第一版支持：

- `start`：入口节点。
- `instruction`：规则或约束说明。
- `step`：必须执行的业务步骤。
- `decision`：条件判断。
- `checkpoint`：状态保存点。
- `human_gate`：人工确认、审批或输入。
- `tool_call`：工具调用。
- `verification`：验证节点。
- `end`：结束节点。
- `failure`：失败处理节点。

### 9.4 边结构

```json
{
  "id": "edge_start_to_step",
  "from": "start",
  "to": "node_explore_context",
  "condition": null,
  "label": "next"
}
```

decision 节点的边必须包含条件：

```json
{
  "id": "edge_decision_yes",
  "from": "node_need_human_review",
  "to": "node_human_gate",
  "condition": {
    "expr": "state.requires_human_review == true"
  },
  "label": "requires review"
}
```

### 9.5 状态结构

```json
{
  "run_id": "run_01",
  "workflow_id": "workflow_using_superpowers",
  "workflow_version": "0.1.0",
  "status": "running",
  "current_node": "node_explore_context",
  "context": {},
  "node_results": {},
  "events": []
}
```

## 10. Skill 到 Workflow 的转换规则

### 10.1 frontmatter

frontmatter 映射到 workflow 元信息：

- `name` -> `workflow.name`
- `description` -> `workflow.description`

### 10.2 Trigger Rules

触发规则映射为 `instruction` 或 `decision` 节点。

如果规则只描述何时适用，生成 `instruction`。

如果规则影响分支，生成 `decision`。

### 10.3 Hard Gate

硬性门禁映射为 `human_gate`、`verification` 或 `guard`。

示例：

- “Do NOT write code until design approved” 映射为 guard。
- “Wait for user approval” 映射为 human gate。
- “Verify tests pass before completion” 映射为 verification。

### 10.4 Checklist

有序 checklist 映射为顺序 `step` 节点。

每个 checklist item：

- 生成一个 `step` 节点。
- 与前后节点建立强顺序边。
- 默认成功路径指向下一步。
- 默认失败路径指向 failure 节点。

### 10.5 Tool Requirements

工具要求映射为 `tool_call` 节点或节点 action。

如果 Skill 明确要求调用某个工具，则生成 `tool_call`。

如果只是说明可使用工具，则生成节点 metadata。

### 10.6 User Approval

用户确认、审批、评审等要求映射为 `human_gate`。

human gate 必须定义：

- 等待对象。
- 提示内容。
- 恢复条件。
- 拒绝后的路径。

### 10.7 Verification Rules

验证规则映射为 `verification` 节点。

verification 节点必须记录：

- 验证命令或验证方法。
- 成功条件。
- 失败路径。

## 11. LiteGraph 映射设计

### 11.1 节点视觉形态

DSL 节点映射到 LiteGraph 节点：

- `start`：入口节点，绿色。
- `step`：业务步骤节点，蓝色。
- `instruction`：规则节点，灰色。
- `decision`：条件节点，黄色。
- `checkpoint`：状态节点，紫色。
- `human_gate`：人工节点，橙色。
- `tool_call`：工具节点，青色。
- `verification`：验证节点，深蓝色。
- `failure`：失败节点，红色。
- `end`：结束节点，绿色。

### 11.2 连线语义

LiteGraph 连线映射为 DSL edge。

保存时必须校验：

- 连线两端节点存在。
- 不能从 `end` 节点连出。
- `decision` 输出必须有条件。
- `human_gate` 必须有 approve / reject 或 continue / cancel 路径。
- 删除连线不能导致死节点。

### 11.3 编辑限制

第一版 Editor 支持：

- 查看节点。
- 拖拽节点。
- 修改节点标题和描述。
- 修改简单参数。
- 查看编译错误。
- 查看运行状态。

第一版 Editor 不支持：

- 复杂多人协作编辑。
- 实时冲突解决。
- 任意自定义节点脚本。
- 未经校验直接发布。

## 12. Durable Executor 设计

### 12.1 执行模型

Executor 以 run 为单位执行 workflow。

执行循环：

1. 加载 published workflow。
2. 创建 run state。
3. 从 entry 节点开始执行。
4. 执行当前节点 action。
5. 保存节点结果。
6. 判断成功、失败或等待。
7. 根据 edge 选择下一节点。
8. 保存 checkpoint。
9. 直到 completed、failed、waiting 或 cancelled。

### 12.2 强制顺序

Executor 只允许从当前节点沿合法 edge 前进。

不提供任意跳转接口。调试模式可以支持管理员指定节点重放，但必须记录审计日志，且不能用于普通执行。

### 12.3 Human Gate

遇到 `human_gate` 时：

- run 状态变为 `waiting`。
- 保存等待原因。
- 保存等待对象。
- 生成恢复 token 或恢复事件条件。
- 收到人工确认后继续执行。
- 收到拒绝后走拒绝路径。

### 12.4 Checkpoint

checkpoint 节点保存：

- 当前上下文。
- 节点结果。
- 外部工具调用摘要。
- 可恢复位置。

系统重启后，Executor 可以从最后一个 checkpoint 或当前等待节点恢复。

### 12.5 失败策略

节点支持：

- `retry`：失败后重试。
- `timeout`：超时后失败。
- `fallback`：失败后进入替代路径。
- `human_escalation`：失败后转人工。

第一版实现 retry、timeout 和 failure path。fallback 和 human escalation 保留 DSL 字段，并在后续版本实现。

## 13. Control Plane 设计

### 13.1 Workflow 版本

workflow 版本状态：

- `draft`：可编辑，不可被普通 run 执行。
- `published`：可执行，不可直接修改。
- `deprecated`：不可创建新 run，但历史 run 可查看。

发布规则：

- draft 必须通过 Validator。
- published 版本不可变。
- 编辑 published workflow 会创建新 draft。

### 13.2 Run 管理

第一版提供：

- 创建 run。
- 查看 run 列表。
- 查看 run 详情。
- 恢复 waiting run。
- 取消 run。

### 13.3 Audit Log

审计日志记录：

- workflow 创建。
- workflow 编译。
- workflow 发布。
- run 创建。
- 节点开始。
- 节点完成。
- 节点失败。
- human gate 等待。
- human gate 恢复。
- run 完成。
- run 失败。

### 13.4 Connector Registry

第一版提供 connector registry 的数据结构和本地 mock connector。

后续支持：

- 飞书。
- 钉钉。
- CRM。
- OA。
- 数据库。
- Webhook。
- 邮件。
- 工单系统。

## 14. 开源项目形态

### 14.1 仓库结构

推荐仓库结构：

```text
skill2workflow/
  packages/
    parser/
    compiler/
    dsl/
    executor/
    litegraph-editor/
    cli/
    connectors/
  examples/
    skills/
    workflows/
  docs/
    concepts/
    specs/
    guides/
  tests/
```

### 14.2 开源许可证

推荐使用 Apache-2.0。

原因：

- 对企业友好。
- 明确专利授权。
- 适合基础设施类项目。
- 方便商业和开源生态共同采用。

### 14.3 README 叙事

README 应该突出：

- Skill 已经解决 AI 能力适配问题。
- 企业落地缺少高可控执行层。
- `skill2workflow` 把 Skill 编译成 Controlled Workflow。
- 本地即可跑通闭环。
- 支持 LiteGraph 可视化。
- 支持 Durable Executor。
- 开放 DSL 和插件接口。

### 14.4 贡献路径

开源贡献可以围绕：

- Skill parser。
- Workflow node type。
- Compiler rule。
- Executor backend。
- LiteGraph node UI。
- Connector。
- Example workflow。
- Enterprise deployment guide。

## 15. 小闭环实现节奏

### Loop 1：Parser 闭环

目标：输入 `SKILL.md`，输出 `Skill IR JSON`。

交付：

- CLI：`skill2workflow parse ./SKILL.md`
- 解析 frontmatter。
- 解析 description。
- 解析 hard gate。
- 解析 checklist。
- 解析 ordered steps。
- 解析 tool hints。
- 输出 `skill.ir.json`。
- 添加测试样例。

成功标准：

- 能解析至少 3 个真实 `SKILL.md`。
- 输出结构稳定。
- 不丢失关键规则和步骤。

### Loop 2：Compiler 闭环

目标：`Skill IR -> Workflow DSL`。

交付：

- CLI：`skill2workflow compile ./SKILL.md -o workflow.json`
- 生成节点。
- 生成边。
- 生成 entry / end。
- 生成基础 failure node。
- 基础 Validator。

成功标准：

- workflow 无孤立节点。
- checklist 能被编译成强顺序步骤。
- hard gate 能被编译成 guard 或 human gate。

### Loop 3：Executor 闭环

目标：workflow 可以被本地强制执行。

交付：

- CLI：`skill2workflow run workflow.json`
- 本地 SQLite 保存 run state。
- 顺序执行 step。
- human gate 暂停。
- resume 命令恢复。
- run log 可查看。

成功标准：

- 不能跳过未完成节点。
- 中断后能恢复。
- 每个节点都有执行记录。

### Loop 4：LiteGraph 闭环

目标：workflow 可以像 ComfyUI 一样可视化。

交付：

- Web UI。
- LiteGraph 加载 DSL。
- 展示节点和连线。
- 展示节点参数。
- 保存后触发 Validator。
- 展示 run 状态。

成功标准：

- 能从 `workflow.json` 渲染图。
- 能编辑简单参数。
- 非法连接会被拦截或标红。

### Loop 5：最小 Control Plane

目标：形成企业产品雏形。

交付：

- workflow draft / published / deprecated。
- workflow version。
- run list。
- run detail。
- audit log。
- connector registry 占位。

成功标准：

- 发布版本不可变。
- run 绑定 workflow version。
- 审计日志能追踪关键事件。

## 16. 技术栈建议

### 16.1 语言

推荐 TypeScript。

原因：

- 前后端共享类型。
- 适合 CLI、编译器、Web UI。
- 生态成熟。
- 方便开源贡献。

### 16.2 CLI

使用 Node.js CLI。

命令示例：

```bash
skill2workflow parse ./SKILL.md
skill2workflow compile ./SKILL.md -o workflow.json
skill2workflow validate ./workflow.json
skill2workflow run ./workflow.json
skill2workflow resume <run-id>
skill2workflow runs
skill2workflow ui
```

### 16.3 UI

推荐 Vite + React 或 Vue。

LiteGraph 可视化层可以单独封装为 `packages/litegraph-editor`，避免和业务逻辑耦合。

### 16.4 存储

第一版使用 SQLite。

保存：

- workflow versions。
- runs。
- node events。
- audit logs。
- connector registry。

### 16.5 Schema

使用 Zod 或 JSON Schema。

要求：

- DSL schema 可发布。
- CLI 和 UI 共用 schema。
- Validator 错误可读。

### 16.6 测试

使用 Vitest。

测试范围：

- Parser fixture。
- Compiler rule。
- Validator rule。
- Executor state transition。
- CLI smoke test。
- LiteGraph adapter serialization。

## 17. 企业扩展路线

### 17.1 权限治理

后续支持：

- workflow viewer。
- workflow editor。
- workflow publisher。
- run operator。
- human approver。
- admin。

### 17.2 审批发布

发布 workflow 前支持审批流：

- 编辑 draft。
- 提交发布。
- 审批人审核。
- 发布为 immutable version。
- 支持回滚到旧版本。

### 17.3 运行监控

监控指标：

- run 成功率。
- run 失败率。
- 平均耗时。
- 节点耗时。
- 卡点节点。
- human gate 等待时间。
- connector 失败率。

### 17.4 部署形态

后续支持：

- 本地开发模式。
- 单机服务器模式。
- 企业私有化部署。
- Kubernetes 部署。
- 云托管控制面。

### 17.5 生态适配

导出和适配方向：

- LangGraph。
- BPMN。
- Temporal。
- n8n。
- Dify。
- Coze。
- Avibe Harness。

这些适配不应替代内部 DSL。内部 DSL 仍然是执行真相源。

## 18. 风险与应对

### 18.1 Skill 结构不稳定

风险：不同 Skill 写法差异较大，Parser 难以完全准确提取。

应对：

- 第一版只支持标准 `SKILL.md`。
- Parser 输出置信度和 source mapping。
- 编译后允许人工在 LiteGraph 中修正。
- 提供 fixture 和贡献指南。

### 18.2 可视化先行导致执行语义弱

风险：项目变成流程图工具，而不是执行控制 runtime。

应对：

- DSL 是执行真相源。
- Executor 只执行 DSL。
- LiteGraph 保存必须重新校验。
- README 强调 runtime-first。

### 18.3 企业能力范围过大

风险：过早做完整企业平台，导致 MVP 迟迟无法交付。

应对：

- 按 5 个小闭环推进。
- 每个 loop 都有可运行命令和成功标准。
- Control Plane 第一版只做最小版本和 run log。

### 18.4 与现有 workflow 引擎定位冲突

风险：被误解为 BPMN、n8n、Dify、LangGraph 的替代品。

应对：

- 明确定位为 Skill 到 Controlled Workflow 的编译和运行层。
- 提供 adapter，而不是直接竞争所有平台。
- 强调兼容和连接。

## 19. MVP 成功标准

MVP 成功标准：

- 可以输入一个真实 `SKILL.md`。
- 可以生成可读的 `Skill IR`。
- 可以生成可执行的 `Workflow DSL`。
- 可以用 LiteGraph 展示 workflow。
- 可以本地运行 workflow。
- 可以在 human gate 暂停和恢复。
- 可以保存 run state 和 audit log。
- 可以证明执行顺序不可跳过。

一句话标准：

> 一个原本只是说明书的 Skill，可以被转换成一个有状态、有顺序、有检查、有暂停、有恢复能力的可执行 workflow。

## 20. 第一阶段边界

第一阶段只承诺：

- 标准 `SKILL.md` 输入。
- 本地 CLI。
- 本地 SQLite。
- 本地 Web UI。
- LiteGraph 可视化。
- 最小 executor。
- 最小 control plane。

第一阶段不承诺：

- 云端服务。
- 多租户。
- 完整 RBAC。
- 完整 BPMN。
- 任意 SOP 文档输入。
- 复杂企业连接器。
- 分布式任务调度。

这个边界能保证项目从第一天开始就有清晰可运行的开源闭环，同时为企业级能力保留自然扩展路径。
