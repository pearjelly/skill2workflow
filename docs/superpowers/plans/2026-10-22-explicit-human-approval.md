# Loop 265: Explicit Human Approval Declarations

## Basis And Decision

The approved design §10.6 maps explicit approval requirements to human gates.
After Loop 264, Chinese numbered processes are preserved, but a Chinese
approval title still becomes a normal step because classification uses English
keywords. Authors need a direct declaration independent of wording.

Use exactly one case-sensitive, single-line suffix, preceded by whitespace:
`<!-- skill2workflow: human_gate -->`. Attach it only to a selected Checklist,
Workflow, or Steps item. The parser removes it from the title/detail and emits
the explicit IR `node_type: human_gate`; compilation uses the existing node,
manual connector, approval successor, and rejection failure path.

## Scope And Compatibility

- Explicit type takes precedence over keyword inference. Unmarked items keep
  their existing behavior and fixtures. Published DSL is not reinterpreted.
- Unknown, duplicate, malformed, empty, or unattached reserved comments fail
  with a fixed error. Case variants of the reserved namespace are rejected.
- Fenced examples do not declare approvals. Legacy Checklist extraction keeps
  its grammar; if it extracts a reserved declaration inside a fence, reject it
  instead of allowing the comment to trigger keyword inference.
- Keep source line/section mapping. The marker must not appear in node IDs,
  titles, descriptions, or approval prompts.
- No new DSL fields, runtime dependencies, prose interpretation, independent
  HARD-GATE positioning, or general replacement of keyword inference.

## Acceptance

Parser/compiler tests first; CLI and real loopback UI parity; fixed UI errors;
Chinese custom quickstart with durable approval and rejection; isolated
installed-wheel CLI/UI compilation; unchanged examples; full supported-Python
CI and release preflight before completion.

## Checks

```bash
PYTHONPATH=src python3 -m unittest tests.test_explicit_approval tests.test_process_steps tests.test_parser tests.test_compiler tests.test_examples tests.test_ui tests.test_package_smoke -q
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop265
```
