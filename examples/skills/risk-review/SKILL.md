---
name: risk-review
description: Controlled risk review workflow with policy checks, analyst approval, and case disposition audit.
---

# Risk Review Skill

Use this skill when an account, transaction, or customer action needs AI-assisted risk review before a hold, release, or escalation decision.

<HARD-GATE>
Do NOT apply a hold, release funds, or close the case until the assigned risk analyst approves the decision.
</HARD-GATE>

## Checklist

1. **Collect review evidence** - gather customer profile, transaction summary, prior decisions, and linked alerts
2. **Check risk signals against policy** - compare evidence against documented policy thresholds and exception rules
3. **Draft risk decision recommendation** - propose hold, release, or escalate with reasoning and required evidence
4. **Ask risk analyst for approval** - wait for analyst approval before changing case disposition
5. **Run case disposition command** - apply the selected hold, release, or escalation state in the case system
6. **Verify risk audit record** - check that evidence, analyst decision, disposition, and timestamp are recorded

## Verification

- Verify the case disposition matches the analyst-approved decision.
- Check that all evidence used for the decision is linked in the audit record.
