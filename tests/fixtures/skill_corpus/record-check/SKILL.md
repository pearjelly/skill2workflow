---
name: record-check
description: Original controlled record-check workflow for the public corpus.
---

## Steps

1. Fetch record <!-- skill2workflow: http {"request":{"url":"https://example.invalid/records","method":"POST"}} -->
2. Validate record <!-- skill2workflow: http_assert {"request":{"url":"https://example.invalid/status"},"assertions":[{"path":"/ready","equals":true}]} -->
3. Prepare summary
4. Reviewer approval
