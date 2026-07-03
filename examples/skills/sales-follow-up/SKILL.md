---
name: sales-follow-up
description: Controlled sales follow-up workflow with approval, CRM update, and audit checks.
---

# Sales Follow-Up Skill

Use this skill when an account team needs AI help drafting a customer follow-up, but customer-facing communication and CRM changes must stay controlled.

<HARD-GATE>
Do NOT send customer-facing follow-up or update CRM until the account owner approves the proposed next action.
</HARD-GATE>

## Checklist

1. **Gather account context** - inspect current opportunity stage, last customer touch, and promised next action
2. **Draft customer follow-up** - prepare a concise follow-up message tied to the current opportunity
3. **Ask account owner for approval** - wait for explicit owner approval before sending or recording changes
4. **Run CRM update command** - record the follow-up, next task, owner, and due date in CRM
5. **Verify follow-up audit trail** - check that the message, task, owner, and timestamp are recorded

## Verification

- Verify that the CRM record contains the approved message and next task.
- Check that the account owner approval is preserved in the run history.
