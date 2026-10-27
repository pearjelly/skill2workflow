# SKILL.md Input Boundary

Explicit [HTTP action declarations](skill-http-actions.md) bind a reviewed
request to a selected step without endpoint inference or compilation-time I/O.

A standalone [trigger input declaration](skill-input-contracts.md) emits the
existing bounded `input_schema` contract. It is workflow-level data, not a step
annotation, and does not alter process selection or infer a gate.

Loop 169 hardens the first step of the compile pipeline: the local `parse` and
`compile` commands now read a user-provided `SKILL.md` through a bounded file
boundary before applying parser heuristics.

## Read Contract

`parse_skill_file` accepts at most **2,097,152 bytes (2 MiB)**. It:

1. requires one regular, non-symlink file;
2. checks the size before opening;
3. opens with no-follow semantics where available;
4. binds the descriptor to the inspected device/inode;
5. reads at most one byte beyond the bound; and
6. rechecks path identity and size after reading.

Oversized, linked, replaced, or growing inputs fail before parser output is
produced. Valid files retain the existing frontmatter, checklist, hard-gate,
section, and source-line mapping behavior. The parser remains dependency-free
and does not treat this source-file limit as a Workflow DSL or trigger-input
limit.

`parse_skill_file` remains a local inspection primitive and may retain its
input path in its in-memory IR. The portable `authoring-export` path replaces
that file reference with the fixed `SKILL.md` before compiling Workflow DSL, so
an exported artifact or derived Bundle cannot disclose the caller's local path.

## Frontmatter Identity And Text

New compilation keeps top-level `name` and `description` separate from the
optional `metadata` string map. `metadata.name` is data, not a replacement
workflow identity. These fields follow the
[Agent Skills frontmatter structure](https://agentskills.io/specification).

```yaml
---
name: reviewed-workflow
description: >-
  Compile reviewed requests.
  Preserve the intended workflow identity.
metadata:
  name: packaging-author
  version: "1.0"
---
```

The compiled ID is `workflow_reviewed_workflow`; the description is the two
sentences joined by a space. Optional metadata is retained in the parsed IR
as a map, not flattened into root fields, emitted into Workflow DSL, inferred
as a gate/tool, or used as runtime authorization.

This dependency-free reader supports a documented YAML **string subset**, not
an arbitrary YAML loader or complete Agent Skills validator:

- Top-level scalar fields and one flat block `metadata` mapping (or `{}`).
  Keys may be plain or single/double quoted. All scalar values stay strings;
  booleans/numbers are not implicitly typed. Existing missing-frontmatter
  fallback and incomplete opening-frontmatter behavior remain unchanged.
- Single-line plain text, single-quoted strings with doubled apostrophes, and
  double-quoted strings using JSON escapes. Whitespace-separated comments are
  removed outside quotes; a URL fragment or quoted `#` stays data.
- Literal `|` and folded `>` blocks, `-`/`+` chomping, and one indentation digit
  in either modifier order. Literal text retains line breaks and extra spaces;
  folding preserves paragraph breaks and more-indented content. Blank blocks,
  CRLF input and quoted/colon-bearing content keep original source-line counts.
  The frontmatter closing delimiter must be a column-zero `---` line, optionally
  followed by spaces/tabs; an indented delimiter inside a scalar is text.

Repeated keys, malformed quotes/indentation, unsupported collections, deeper
maps, tags, anchors, aliases and merge keys fail with the fixed
library `ValueError` text `Invalid SKILL.md frontmatter`, without source values.
The CLI adds a fixed reason, approximate original line when known, and a next
edit; it never repeats field names, values, source excerpts or local paths.
Wrapped plain
or quoted multiline strings, YAML-only quoted escapes and nonempty flow maps
are unsupported; use the block-scalar forms above. No constructors, includes,
filesystem reads or variable evaluation are available. The existing 2 MiB
Skill boundary still applies before parsing.
Key separators and unquoted comments use linear scans rather than padding-
sensitive backtracking. The regression includes long malformed keys and long
valid scalar padding under an owned child-process timeout; it is not a hard
latency SLA for arbitrary operating-system stalls.

This corrects newly generated identity and description. A Skill that relied on
old nested-key flattening, duplicate last-key wins, quote stripping or literal
comment/header markers may now compile differently or be refused. Review the
new Workflow DSL identity and structural diff before explicit publication;
published artifacts are never recompiled, renamed or migrated automatically.
The Workflow DSL, execution and input contracts remain unchanged.

## Recover From A Compile Refusal

In the editor, read the inline reason beside the compile actions, correct the
local file, choose it again and explicitly select **Compile SKILL**. A refused
Skill does not invalidate or replace the already loaded graph. Changing the
selection or draft invalidates pending compile results and clears old feedback.
Unknown errors remain generic rather than guessing which source edit is needed.

`POST /api/v1/skill-compiles` still returns exactly
`{"error":"skill compile rejected"}` for an ordinary compile refusal by default.
An optional **boolean** `diagnostics: true` in the existing `skill_markdown`
request opts into an additional `diagnostic` object; `false` preserves the
legacy response. Invalid envelopes/flags receive only the existing fixed
malformed-body error. Successful responses remain unchanged.

The [diagnostic schema](../schemas/skill-compile-diagnostic-0.1.0.schema.json)
requires exactly `schema_version`, `code`, and `line`. The version is
`skill2workflow-skill-compile-diagnostic-0.1.0`; codes are
`frontmatter_duplicate_key`, `frontmatter_invalid`, `frontmatter_unsupported`,
or generic `skill_invalid`. `line` is a one-based original source line or null;
text-block errors may point near the declaration rather than the precise
malformed character. It includes no source text, keys, values, paths, or raw
exception messages. This is repair evidence, not full YAML validation or a new
Workflow DSL/execution contract.

The editor consumes at most 1 KiB of strict UTF-8 error evidence, accepts only
the known version/shape and source-bounded line, and maps it to fixed copy.
Unknown, malformed, oversized and older-helper responses use safe fixed
fallback guidance. Static hosting still requires `skill2workflow ui` or CLI
compilation; a network/helper failure is distinct from a source refusal.

## Explicit Workflow Version

One standalone `<!-- skill2workflow: workflow_version 0.2.0 -->` in the body
selects the generated workflow version across compile, editor, export, repair
and custom quickstart. It is removed before step extraction and guidance
inference, without shifting source lines. It is not approval or permission to
replace a published artifact. See [versioned Skill iteration](skill-workflow-versions.md)
for the bounded token grammar, fixed refusal, unchanged `0.1.0` default, Bundle
comparison and separate immutable publication. Ordinary `metadata.version`
remains unrelated data; no version is inferred from it.

## Explicit Human Approval

Explicit result checks can use the same selected-step placement with
`<!-- skill2workflow: http_assert {JSON} -->`. See
[Skill HTTP assertions](http-json-assertions.md#declare-a-check-in-skillmd) for
the JSON contract and the approval/check/delivery journey. Only one declaration
may be attached to a step; multiple declarations are rejected.

Authors can require a human decision on a selected Checklist, Workflow, or
Steps item by appending exactly `<!-- skill2workflow: human_gate -->`, with
whitespace before the comment:

```markdown
## Workflow
1. 整理草稿
2. 等待负责人审核 <!-- skill2workflow: human_gate -->
3. 输出结果
```

The declaration overrides keyword inference and is removed from the compiled
title, description, node ID, and approval prompt. Source lines are preserved.
The existing manual human gate waits durably; approval continues to the next
step and rejection follows the failure path. Review the generated draft before
publishing it.

The syntax is case-sensitive, single-line, and permits one marker at the end
of one nonempty selected item. Within the Skill body, unknown, malformed,
repeated, or unattached reserved `skill2workflow` comments fail with
`Invalid Skill step annotation`.
The separately documented standalone `input_schema` and `workflow_version`
declarations are explicit exceptions to selected-step placement and have their
own fixed refusal messages.
This includes a declaration in a process excluded by Checklist precedence.
Examples inside supported fences do not declare approvals or become process
steps. Unmarked items outside fences retain their historical inference rules.
This changes newly compiled drafts only; published workflows retain their DSL.

## Explicit Process Sections

Checklist extraction keeps its existing precedence and list formats, including
headings such as `Verification Checklist`. Even an empty Checklist section
prevents fallback to another process section.

When no Checklist section is recognized, the parser accepts one populated
ATX heading named exactly `Workflow` or `Steps` (case-insensitive):

```markdown
## Workflow
1. **Prepare output** — use the reviewed draft
2. Ask user for approval
3. Deliver output
```

The same numbered process under `## Steps` compiles identically except for
source-section metadata. The fallback rules are deliberately explicit:

- Heading depth and ancestor names do not change eligibility. `Workflow notes`
  is not an eligible heading; a heading's optional closing `#` markers are
  allowed. Illustrative processes must be fenced, even under `Examples`.
- Only direct numbered items (`1.` or `1)`) become steps. The next heading,
  including a child heading, ends that section's content. Numbering may repeat
  or start above one; source order determines execution order.
- Top-level list markers must use consistent indentation of zero to three
  spaces. The smallest indentation among all direct list markers establishes
  the top level. Deeper numbered items, bullet inventories, indented code,
  and prose do not become steps. A numbered sublist beneath `- Notes` is not
  promoted into a process.
- Backtick and tilde fences are ignored in Checklist, Workflow and Steps
  extraction. A closing fence must use the same character and at least the
  opening length; an unclosed fence excludes the remaining text. Fences may
  have up to three leading spaces. A backtick fence's info string cannot
  contain a backtick.
- Empty candidate sections are ignored. More than one populated `Workflow`
  or `Steps` section is rejected with a fixed error; consolidate the intended
  process into one section or use an explicit Checklist. Separate procedures
  are never silently concatenated.

The parser preserves title/detail splitting, original line numbers, and section
names in the IR and compiled node source metadata. Compilation still produces a
draft for review; this grammar neither executes prose nor makes standalone
hard-gate declarations executable. Existing node typing and human-gate behavior
are unchanged. Newly recognized steps can therefore introduce existing tool or
approval nodes: review the generated DSL before publishing or running it.

The same supported fence rules exclude examples from tool, approval, verification and
hard-gate hints. Fenced text remains visible within its containing IR section,
but its headings do not create sections. Newly compiled Skills that previously
treated fenced examples as real steps or hints may generate a different draft;
compare and review it before publishing. Existing published artifacts are not
recompiled or changed. Fences indented by four or more spaces and fences inside
Markdown container syntax are not recognized by this bounded subset; their
contents may be interpreted as steps or guidance. Move examples to a supported
top-level fence before compiling.

## Verification

`tests/test_parser.py` covers pre-open size rejection, symlink rejection,
path-replacement fencing, growth rejection, and existing parser compatibility.
The focused command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_parser -v
PYTHONPATH=src python3 -m unittest tests.test_process_steps -v
```

This is a local authoring-input boundary only. It does not add remote upload,
arbitrary document conversion, multi-tenant isolation, or a guarantee that
parser heuristics understand every possible Markdown dialect.

## Optional Compile Review

`compile --review` also emits the fixed
`skill2workflow-skill-compile-review-0.1.0` summary. With `-o`, standard output
is only the review so a local script can store the normal Workflow DSL artifact
and inspect source-free counts/notices separately. Without `-o`, the explicit
JSON wrapper contains both the normal draft and the review; plain `compile`
retains its DSL-only compatibility output.

The review contains only inferred structural counts and the finite notices
`checklist_not_found`, `human_gate_not_inferred`, and
`verification_not_inferred`. It does not include Skill text, local paths,
credentials, validation of business intent, or authorization to publish/run.
The historical `checklist_not_found` code means that no supported ordered steps
were found, including the `Workflow`/`Steps` fallback; its schema and spelling
remain unchanged.
