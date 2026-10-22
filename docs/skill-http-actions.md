# Declare HTTP Actions In A Skill

An explicit `http` step compiles directly into the existing HTTP tool-call
binding. You do not need to edit the generated DSL to attach the request.

Use a standalone [typed trigger input declaration](skill-input-contracts.md)
to require and constrain mapped business fields before trigger admission. The
complete example Skill includes that source-level contract.

```markdown
## Steps
1. 负责人审批 <!-- skill2workflow: human_gate -->
2. 提交请求 <!-- skill2workflow: http {"request":{"method":"POST","url":"https://example.invalid/tasks","body":{"source":"workflow"}}} -->
3. 校验结果 <!-- skill2workflow: http_assert {"request":{"url":"https://example.invalid/tasks/status"},"assertions":[{"path":"/ready","equals":true}]} -->
4. Deliver result
```

The endpoints above are reserved placeholders, not a live integration. Replace
them with a reviewed API and matching result contract. For ID-based input
mapping and credential handles, start from the complete
[example Skill](../examples/skills/http-action-flow/SKILL.md) and inspect its
[compiled DSL](../examples/workflows/http-action-flow.workflow.json).

## Declaration Contract

Append one single-line declaration to a nonempty selected Checklist, Workflow,
or Steps item. The existing section precedence, fence rules, and one-marker
limit apply. Configuration has exactly `request` plus optional `credentials`;
unknown fields and malformed, duplicate-key, or nonfinite JSON are rejected
with `Invalid Skill step annotation`. Literal nested HTML comment delimiters
are rejected; use JSON Unicode escapes when those characters are data.

The request supports existing HTTP fields:

- `url`: required reviewed HTTP/HTTPS endpoint without embedded credentials;
- `method`: optional ASCII HTTP token, at most 32 bytes; runtime defaults to
  GET and uppercases the method;
- `headers`: string names and values, at most 64 entries / 65,536 UTF-8 bytes;
- `body`: optional JSON value, at most 1 MiB encoded as UTF-8 JSON;
- `input_mapping`: existing `/input/...` sources to `/body/...` or
  `/query/<name>`, with optional boolean `required` (default true);
- `allowed_origins`: optional exact-origin allowlist, subject to service-wide
  origin policy as well;
- `timeout_ms`: integer 0–86,400,000; zero retains the HTTP runtime's default
  timeout rather than disabling it;
- `response_mode`: `metadata` by default for these new declarations, or
  explicit `full` when retaining provider response values is necessary.

The 16,384-byte URL bound, metadata character checks, redirect rejection,
direct transport, and response-size/UTF-8 boundaries remain the existing
[HTTP connector contract](connectors.md). Header credential descriptors use
exactly `target`, `name`, and `handle`: target is `header`, with at most 32
descriptors and 1,024 UTF-8 bytes per handle. Credential header names count
toward the request metadata bounds. Body mappings require an object body or
the omitted/null body that runtime initializes as an object.

Compilation copies bindings, preserves original source lines, and removes
the marker from node title/description/ID. Parsed configuration values do not
become inferred rules or tool/approval/verification hints. Ordinary HTTP actions
do not count as verification nodes merely because a request completed.

## Review, Publish, And Run

Compile and validate the example, review its request and transitions, then
publish only after replacing the placeholder endpoints. Supply this non-secret
input through a local JSON file:

```json
{"record_id":"reviewed-record-001","title":"Example task"}
```

```bash
skill2workflow compile ./SKILL.md --review -o ./workflow.json
skill2workflow validate ./workflow.json --format json
skill2workflow publish ./workflow.json --state-dir ./state --storage sqlite
skill2workflow trigger workflow_http_action_flow --version 0.1.0 \
  --state-dir ./state --storage sqlite --source local-cli \
  --idempotency-key reviewed-request-001 --input ./input.json
skill2workflow resume-published <run_id> --state-dir ./state --storage sqlite \
  --credential-file /absolute/private/credentials.json
```

Use the actual workflow ID shown by compilation when editing the Skill name.
The example pauses before POST; `--reject` stops it without calling the API.
Approving sends mapped input, then checks the result endpoint. HTTP failure or
a mismatching assertion stops delivery. Missing required input and disallowed
origins fail before the outbound call and credential resolution.

The declaration itself does not add approval. A workflow without a preceding
human gate may call the endpoint as soon as it is run. Compilation, validation,
and publication make no HTTP request and resolve no credentials. Review and
publish/run are separate actions.

Use handles rather than literal secrets. Trigger input is durable business
data; it is not a secret store. New-declaration metadata mode discards response
body/headers, including error responses. Explicit full mode retains them under
the legacy HTTP contract. Neither mode changes provider effects, retry behavior,
or exactly-once guarantees. Existing DSL and unmarked Skill inference keep their
previous behavior and retention defaults. Credential-file format is defined in
the [credential boundary guide](credential-boundary.md).

## Local Qualification

Run the isolated loopback journey without a live provider:

```bash
python3 scripts/skill_http_action_smoke.py
```

It compiles and publishes the Skill, triggers input, resumes the human gate,
performs real POST/GET requests, and verifies match, mismatch, HTTP failure,
rejection, successor suppression, and response/credential exclusion. Package CI
runs the same journey against the installed wheel with source imports disabled.
