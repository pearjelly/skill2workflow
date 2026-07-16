# Lark/Feishu Live Connector Validation

Validation timestamp (UTC): `2026-07-16T07:08:40Z`

Observed compact result:

- connector_id: `lark_task`
- operation: `create_task`
- mode: `live`
- credential_status: `resolved`
- idempotency_key_present: `true`
- provider_status: `completed`
- lark_task_id_present: `true`
- assignee_present: `true`

The validation task was assigned to the consenting current user and retained as visible evidence.

A standard-tier short-lived Vault credential was used as a one-time fallback after passkey/WebAuthn could not be provisioned. It was constrained to the fixed connector endpoint and removed immediately after success.

Raw task values, user ids, credentials, request bodies, response bodies, and task ids are intentionally omitted.

Offline verification commands run before the live write:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py examples/connectors/lark_task_connector.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
git diff --check
```
