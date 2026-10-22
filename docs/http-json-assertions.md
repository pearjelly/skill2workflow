# Executable HTTP JSON Assertions

## Declare A Check In SKILL.md

Append a single-line JSON declaration to the selected step. The compiler builds
the connector and transitions for you:

```markdown
## Workflow
1. 整理结果
2. 负责人审批 <!-- skill2workflow: human_gate -->
3. 校验接口结果 <!-- skill2workflow: http_assert {"request":{"url":"https://example.invalid/result"},"assertions":[{"path":"/ready","equals":true}]} -->
4. 交付结果
```

Replace the example endpoint with your reviewed result endpoint. `request`
and `assertions` are required; optional `credentials` contain header handle
descriptors, never resolved values. Request options include GET, headers,
timeout, allowed origins, query input mapping, and full response mode. The
declaration rejects unknown configuration/request fields, malformed or
duplicate-key JSON, invalid scalar checks, and literal comment delimiters
inside the JSON. Use JSON Unicode escapes for delimiter characters when they
are part of an expected string. Credential descriptors are limited to 32
header handles of at most 1,024 UTF-8 bytes each.

The declaration must be on one nonempty selected Checklist/Workflow/Steps
item and takes precedence over keyword inference. Use separate steps for
approval and checking. It is removed from the displayed title, description,
and node ID; source lines remain available. Invalid declarations use the fixed
`Invalid Skill step annotation` error. Compilation reads no credentials and
makes no HTTP request. Normal compile review includes this connector in its
verification count, which does not prove execution.
Parsed configuration values are excluded from legacy rule/hint scanning, so
an expected string containing rule-like words or tags remains comparison data.

```bash
skill2workflow compile ./SKILL.md --review -o ./workflow.json
skill2workflow validate ./workflow.json --format json
```

Review and publish the resulting workflow through the existing handoff. During
execution, the approval waits before the endpoint is called; rejection stops
the run. An approved run delivers only if all response assertions match.

## Review In The Editor

Select the compiled `http_assert` node. Its **HTTP assertion** panel shows the
method and endpoint, every typed JSON comparison, and the source DSL's
**On match** / **On failure** destination names and IDs. For example, `true`
and `"true"` remain visibly different values. Expand **Connector configuration**
to inspect the complete stored binding, including request mappings and
credential handle descriptors.

The panel is read-only: selection makes no request and resolves no credentials.
To change a check, update the Skill declaration or source DSL and reload it.
Configured values remain visible; never embed secrets in expected values or
literal headers. Existing allowlisted node edits and ordinary HTTP connector
editing are unchanged. Save and validate the DSL before publication; the graph
and review panel do not become execution authorities.

## Bind Directly In Workflow DSL

Use the explicit `http_assert` connector on a `tool_call` node to fetch a
result endpoint and require JSON fields to match expected values. A matching
HTTP status alone is insufficient: all assertions must pass before the node
follows `on_success`; a mismatch follows its normal `on_failure` path.

```json
{
  "id": "verify_result",
  "type": "tool_call",
  "title": "Verify result readiness",
  "on_success": "deliver",
  "on_failure": "failure",
  "connector": {
    "id": "http_assert",
    "kind": "http_assert",
    "request": {
      "method": "GET",
      "url": "https://example.invalid/results/123",
      "allowed_origins": ["https://example.invalid"],
      "timeout_ms": 5000
    },
    "assertions": [
      {"path": "/ready", "equals": true},
      {"path": "/result/status", "equals": "complete"}
    ]
  }
}
```

Supply a real reviewed endpoint and matching transition edges in your DSL,
then validate it before publication. This connector is not inferred from free
prose; the explicit Skill declaration above is also supported. Existing inferred `verification` nodes remain descriptive completion
markers; their presence does not prove that a result was checked. This
explicit connector performs the network request and comparisons.

## Request And Assertions

Only exact uppercase `GET` (or the omitted default) is supported. A `body`
property is rejected even when null. Existing credential handles, timeout,
allowed origins, service-wide origin policy, direct transport, redirect
rejection, and strict UTF-8/1 MiB response bounds apply. Input mapping may
target query parameters only. Response mode is `full` internally for checking;
`metadata` is rejected because it discards the content needed by assertions.
The response is discarded after comparison in either outcome.

Provide 1–16 checks. Each object has exactly `path` and `equals`:

- `path` is a JSON pointer, at most 1,024 UTF-8 bytes and 32 tokens. Empty
  pointer selects the root. `~1` means `/`; `~0` means `~`. Array indexes use
  canonical decimal notation (`0`, `1`, …), with at most nine digits.
- `equals` is a JSON scalar: string, finite number, boolean, or null. Its
  UTF-8 JSON encoding is at most 4,096 bytes. Objects and arrays are excluded.
- All checks must match. Missing values fail, including missing versus null.
  JSON numbers compare numerically; booleans never match numeric zero or one.
- Invalid JSON, duplicate object keys, nonfinite numbers, and numeric literals
  longer than 128 characters fail. No code or expressions are evaluated.

Invalid configuration fails before credentials or network access. Connector
results retain only HTTP status, assertion count, a match boolean, and a fixed
error. They exclude response bodies, headers, compared values, and paths.
Expected values remain part of the workflow artifact; use non-secret business
expectations, not secrets. Network failures retain the existing fixed HTTP
failure boundary.

## Runtime And Compatibility

The connector uses ordinary tool-call retries, failure transitions, cancellation,
and deadlines. It performs one GET per attempt and does not poll. GET endpoints
can still have provider effects; use a reviewed read endpoint and retry policy.
An older runtime rejects the unknown connector ID instead of silently treating
the request as successful HTTP. The DSL remains `0.1.0`; deploy a runtime that
lists `http_assert` before publishing this binding. Existing HTTP and inferred
verification nodes keep their behavior.

Run the real loopback CLI qualification:

```bash
python3 scripts/http_assertion_smoke.py
python3 scripts/http_assertion_smoke.py --executable /path/to/installed/skill2workflow
```

The installed mode clears source-import assistance and verifies matching and
failing responses, SQLite results, successor suppression, and response-value
discarding. CI runs it against the qualified wheel on Python 3.9 and 3.14.
