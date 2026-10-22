---
name: http-action-flow
description: Approve a reviewed HTTP action, submit trigger input, and verify the result before delivery.
---

# HTTP Action Flow

Use this illustrative workflow only after replacing the reserved example
endpoints and origins with a reviewed API contract. The service must accept a
client-supplied record ID and expose that ID through its result endpoint.
Provide non-secret `record_id` and `title` trigger inputs. Resolve the
`task_api_token` header handle through a separate private credential provider.
POST can create provider-side effects; neither approval nor trigger replay
protection guarantees exactly-once effects. This example adds no retries.

<!-- skill2workflow: input_schema {"type":"object","properties":{"record_id":{"type":"string","minLength":1,"maxLength":64},"title":{"type":"string","minLength":1,"maxLength":200}},"required":["record_id","title"],"additionalProperties":false} -->

## Steps

1. 负责人审批 <!-- skill2workflow: human_gate -->
2. 提交请求 <!-- skill2workflow: http {"request":{"method":"POST","url":"https://example.invalid/tasks","allowed_origins":["https://example.invalid"],"body":{"source":"skill2workflow"},"input_mapping":[{"from":"/input/record_id","to":"/body/id"},{"from":"/input/title","to":"/body/title"}]},"credentials":[{"target":"header","name":"Authorization","handle":"task_api_token"}]} -->
3. 校验结果 <!-- skill2workflow: http_assert {"request":{"url":"https://example.invalid/tasks/status","allowed_origins":["https://example.invalid"],"input_mapping":[{"from":"/input/record_id","to":"/query/id"}]},"credentials":[{"target":"header","name":"Authorization","handle":"task_api_token"}],"assertions":[{"path":"/ready","equals":true}]} -->
4. Deliver result
