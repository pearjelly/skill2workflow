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

## Verification

`tests/test_parser.py` covers pre-open size rejection, symlink rejection,
path-replacement fencing, growth rejection, and existing parser compatibility.
The focused command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_parser -v
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
