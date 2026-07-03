---
name: operations-analysis
description: Controlled operations analysis workflow with metric query, threshold checks, owner confirmation, and action tracking.
---

# Operations Analysis Skill

Use this skill when an operations team needs AI help turning metrics into an action plan while preserving owner review and follow-up accountability.

<HARD-GATE>
Do NOT publish the operating action plan until the responsible business owner confirms the narrative and actions.
</HARD-GATE>

## Checklist

1. **Run metrics query command** - collect the KPI slice, date range, and source system outputs
2. **Check threshold breaches** - identify metrics outside expected thresholds and note affected business areas
3. **Draft operating narrative** - explain drivers, impact, assumptions, and recommended actions
4. **Ask business owner to confirm action plan** - wait for owner confirmation before publishing the plan
5. **Publish operating actions** - record action owners, due dates, and follow-up cadence
6. **Verify action owners and follow-up dates** - check that every action has an owner, due date, and review point

## Verification

- Verify every action item has an owner and due date.
- Check that metric sources and assumptions are preserved in the run history.
