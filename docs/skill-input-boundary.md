# SKILL.md Input Boundary

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
- Backtick and tilde fences are ignored in the fallback. A closing fence must
  use the same character and at least the opening length; an unclosed fence
  excludes the remaining text. Legacy Checklist parsing is unchanged.
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
