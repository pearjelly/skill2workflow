# Iterate A Skill As A New Workflow Version

Published workflow versions are immutable. Editing a Skill and compiling it
again does not permit replacing its previously published version. Declare the
next intended version in the Skill itself instead of editing generated JSON:

```markdown
---
name: team-review
description: Review a team deliverable before delivery.
---
<!-- skill2workflow: workflow_version 0.1.0 -->

## Steps
1. Review <!-- skill2workflow: human_gate -->
2. Deliver reviewed output
```

Compile and inspect the version before publishing:

```bash
skill2workflow authoring-export ./SKILL.md --output-dir ./review-v1
skill2workflow authoring-verify ./review-v1
skill2workflow authoring-bundle ./review-v1 -o ./review-v1.s2w
```

After changing the process, change only the declaration's version token to
`0.2.0`. Keep the Skill name if it is the same workflow. Create a separate
review set and compare the two verified Bundles before publication:

```bash
skill2workflow authoring-export ./SKILL.md --output-dir ./review-v2
skill2workflow authoring-verify ./review-v2
skill2workflow authoring-bundle ./review-v2 -o ./review-v2.s2w
skill2workflow bundle-diff ./review-v1.s2w ./review-v2.s2w
```

The diff is a value-free structural aid, not business approval. A version-only
change need not report changed steps. Inspect the actual DSL and review before
explicit publication into your local control plane:

```bash
skill2workflow authoring-publish ./review-v1 --state-dir ./state --storage sqlite
skill2workflow authoring-publish ./review-v2 --state-dir ./state --storage sqlite
skill2workflow workflow-diff workflow_team_review \
  --from-version 0.1.0 --to-version 0.2.0 --state-dir ./state --storage sqlite
```

Use the actual compiled workflow ID if you change the Skill name. These commands
publish only; they do not start a run, approve a human gate, resolve credentials
or call a provider. Use the existing [service release handoff](authoring.md#preflight-and-publish-to-a-self-hosted-service)
when publishing remotely. Alias promotion remains a separate explicit operation.
No automatic version increment, overwrite, migration or alias change occurs.

## Declaration Contract

The case-sensitive marker is single-line and standalone, with zero to three
leading spaces and optional trailing whitespace. Put it once in the body,
outside backtick/tilde fenced examples. Do not append it to a step or prose.

The token is **1–128 ASCII characters**, begins with a letter or digit, and
otherwise uses letters, digits, `.`, `_` or `-`. For example, `0.2.0` and
`0.2.0-rc.1` are accepted. Paths, whitespace, quotes, non-ASCII characters and
`+` build suffixes are not supported by this bounded authoring subset. This is
not a new restriction on existing manually authored Workflow DSL versions.

Malformed, duplicate or misplaced recognized declarations fail with the fixed
`Invalid Skill workflow version declaration` error without echoing their
content. Invalid input leaves compile/export/quickstart outputs uncreated;
backed-up repair also refuses before replacing an existing set. Correct the
source and rerun the explicit command. Compiler callers supplying Skill IR are
subject to the same validation without coercion.

Omitting the declaration keeps **`0.1.0`**. Ordinary root/optional metadata
fields named `version` do not establish workflow deployment intent. Only the
new IR `workflow_version` and generated `workflow.version` carry the selected
token. Package version, DSL `schema_version`, identity, source-line mapping,
node inference, gates, review/report schemas and execution policy are unchanged.
The declaration is removed before step extraction and guidance inference.

## One Version Across Authoring Paths

Plain `compile`, `compile --review`, the local editor compile helper,
`authoring-export`, backed-up `authoring-repair` (including `--dry-run`) and
custom-Skill `quickstart` read the same source declaration. Repair rebuilds the
version in the selected source; it does not guess a version from damaged files.
Keep the intended declaration when recovering a set, and inspect the preview
before replacement. Existing no-declaration Skills and fixtures retain their
default version and output.

An existing waiting run remains bound to its original immutable workflow
version. Publishing `0.2.0` does not redirect or resume a `0.1.0` run. Starting
the new version, supplying input, approving it, and promoting an alias all
remain separate controlled actions. Publishing different contents as an already
published `workflow_id@version` is still refused; choose a new reviewed version.

## Qualification

```bash
PYTHONPATH=src python3 -m unittest tests.test_skill_workflow_version -v
python3 scripts/skill_version_smoke.py
python3 scripts/skill_version_smoke.py --executable /path/to/installed/skill2workflow
```

The installed wheel gate requires actual compile, artifact verification, backed-
up repair/preview, Bundle diff, two-version publication, immutable-conflict
preservation, version-pinned approval/rejection, custom quickstart, local helper
and invalid-source refusal evidence. It uses synthetic manual steps, owned local
state and loopback only, not a live provider or credential. Incomplete evidence
fails qualification; source imports and help markers do not substitute for it.
