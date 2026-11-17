---
name: risk-routing
description: Fetch a risk record and enforce manual or automatic approval through explicit decisions.
---

# Risk Routing

Replace the reserved example endpoints with reviewed APIs before running.
Full response retention is explicit because the decision reads the JSON risk
field. High-risk records or large amounts require a human decision; only the
default path calls the automatic approval API. Manual approval terminates its
own path, so it never also calls the automatic action. Rejection fails the run.

<!-- skill2workflow: input_schema {"type":"object","properties":{"amount":{"type":"number","minimum":0}},"required":["amount"],"additionalProperties":false} -->

## Steps

1. Fetch risk <!-- skill2workflow: http {"request":{"url":"https://example.invalid/risk","response_mode":"full"}} -->
2. Route risk <!-- skill2workflow: decision {"branches":[{"when":{"path":"/nodes/1/output/body/risk","equals":"high"},"to":3},{"when":{"path":"/input/amount","gt":10000},"to":3}],"default":4} -->
3. Manual approval <!-- skill2workflow: human_gate {"next":"end"} -->
4. Automatic approval <!-- skill2workflow: http {"request":{"url":"https://example.invalid/approve","method":"POST"}} -->
