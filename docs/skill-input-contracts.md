# Declare Trigger Inputs In A Skill

A Skill can declare the existing Workflow DSL `input_schema` without editing
compiled JSON. Put one standalone declaration in the Skill body:

```markdown
---
name: reviewed-request
description: Approve a request with explicit business inputs.
---

<!-- skill2workflow: input_schema {"type":"object","properties":{"record_id":{"type":"string","minLength":1,"maxLength":64},"title":{"type":"string","minLength":1,"maxLength":200}},"required":["record_id","title"],"additionalProperties":false} -->

## Steps
1. 负责人审批 <!-- skill2workflow: human_gate -->
2. Deliver reviewed request
```

The complete [HTTP action example](../examples/skills/http-action-flow/SKILL.md)
combines typed inputs, explicit approval, POST input mapping and a GET result
check. Its [compiled DSL](../examples/workflows/http-action-flow.workflow.json)
contains the contract at top-level `input_schema`.

## Declaration Boundary

The declaration is case-sensitive, single-line and standalone, with zero to
three leading spaces. It may appear anywhere in the body outside backtick or
tilde fenced examples. It must not be attached to prose or a step. Declare it
once; duplicates are rejected, not merged. Ordinary frontmatter fields do not
declare an input contract. Existing Checklist/Workflow/Steps precedence remains
unchanged.

The JSON object uses the existing bounded
[trigger input subset](workflow-dsl-contract.md#declarative-trigger-input-contracts):

- Root type `object`; nested object, array, string, integer, number, boolean or null.
- Declared properties, required fields, additional-property policy, array items,
  string length, numeric bounds and typed enum values.
- At most **64 KiB** of raw declaration JSON and canonical schema JSON, eight
  nesting levels, 128 properties per object and 128 enum entries.
- Unsupported keywords such as `$ref`, `pattern` and `default` are rejected;
  there is no default injection, type coercion, expression evaluation or full
  JSON Schema support.

Malformed, duplicate-key, nonfinite or out-of-bounds recognized declarations
fail with `Invalid Skill input schema declaration`. Literal nested HTML comment
delimiters are refused; use JSON Unicode escapes if those characters are data.
No invalid declaration is partially compiled, and CLI refusal leaves an existing
output artifact unchanged. The local editor compile endpoint retains its fixed
`skill compile rejected` response without source values.

The active declaration is removed before guidance inference, not interpreted
as approval, verification, a hard gate or a tool hint. Its strings remain data.
Node source lines are preserved. The compiler revalidates explicit IR and copies
the contract. Fenced examples do not declare a workflow contract.

## Compile, Publish And Trigger

Review the compiled `input_schema` and business steps before publication:

```bash
skill2workflow compile ./SKILL.md --review -o ./workflow.json
skill2workflow validate ./workflow.json --format json
skill2workflow publish ./workflow.json --state-dir ./state --storage sqlite
```

Create a non-secret input JSON file, for example:

```json
{"record_id":"reviewed-record-001","title":"Example task"}
```

Use the actual compiled workflow ID:

```bash
skill2workflow trigger workflow_reviewed_request --version 0.1.0 \
  --state-dir ./state --storage sqlite --source local-cli \
  --idempotency-key reviewed-request-001 --input ./input.json
skill2workflow resume-published <run_id> --state-dir ./state --storage sqlite
```

HTTP examples also need reviewed endpoints/origins and a private credential
provider when their explicit gate is approved. A contract itself does not add an
approval gate or authorize any effect.

Missing, wrong-typed, out-of-range and disallowed extra input is rejected before
the trigger idempotency claim, run creation, audit emission, credential resolution
or outbound request. Errors identify the contract path but do not echo rejected
values. A rejected input does not consume its idempotency key; a corrected input
can be submitted under that same unused key.

This is specifically **trigger admission**, including the existing webhook,
service and recurring-trigger paths. It does not add validation to raw
`LocalExecutor` contexts or direct `run`/`run-published` calls without a trigger.
The current `quickstart --skill` first run also has no trigger input; use the
compile → publish → trigger path above for a Skill requiring business inputs.
Do not treat an empty-input quickstart run as validation of this contract.

## Compatibility And Qualification

Only newly compiled explicit declarations gain the field. Skills without the
declaration retain open-object trigger input behavior; published DSL artifacts
are not recompiled, changed or reinterpreted. DSL version, validator semantics,
human decisions, connector effects, response retention and write-back permissions
are unchanged. The contract survives graph export and strict CLI write-back,
but is not editable through generic node parameter controls.

Trigger input is durable business data, not a secret store. Use credential
handles outside the schema/input payload for authentication. Compilation,
validation and publication perform no provider call or credential resolution.

```bash
PYTHONPATH=src python3 -m unittest tests.test_skill_input_schema -v
python3 scripts/skill_http_action_smoke.py
```

The seven-case HTTP journey checks three admission refusals, a corrected retry,
approval, rejection, successful delivery, HTTP failure and result mismatch on
an isolated loopback server. It proves no claims/runs/audit/requests on invalid
input and runs against the isolated installed wheel in package CI.
