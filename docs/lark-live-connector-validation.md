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

The user explicitly approved a one-time standard-tier Vault fallback after protected-tier passkey/WebAuthn provisioning failed. The credential had `open.feishu.cn` allowed-host metadata, was short-lived, and was deleted immediately after success.

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
