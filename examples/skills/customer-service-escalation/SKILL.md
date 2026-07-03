---
name: customer-service-escalation
description: Controlled customer service escalation workflow with SLA checks, lead approval, and handoff audit.
---

# Customer Service Escalation Skill

Use this skill when a support case may need escalation and the team needs AI assistance without bypassing service policy.

<HARD-GATE>
Do NOT notify the customer or reassign the case until the support lead approves the escalation plan.
</HARD-GATE>

## Checklist

1. **Classify customer issue** - summarize the symptom, affected customer, product area, and current severity
2. **Check SLA and customer history** - compare the case against SLA commitments and recent customer interactions
3. **Draft escalation plan** - identify target owner, escalation reason, customer message, and expected response time
4. **Ask support lead for approval** - wait for support lead approval before handoff or customer notification
5. **Run support handoff command** - create the escalation task and notify the assigned owner
6. **Verify escalation acknowledgement** - check that the owner, SLA target, and acknowledgement timestamp are recorded

## Verification

- Verify the escalation owner acknowledged the handoff.
- Check that the customer-facing message matches the approved escalation plan.
