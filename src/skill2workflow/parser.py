"""Parse standard SKILL.md files into a Skill IR."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Dict, List, Tuple
from .http_assertions import load_assertion_json, skill_http_assertion_binding
from .skill_http import skill_http_action_binding
from .input_schema import INPUT_SCHEMA_MAX_BYTES
from .skill_input import SKILL_INPUT_SCHEMA_ERROR, skill_input_schema_contract
from .frontmatter import parse_frontmatter


SkillIR = Dict[str, object]
MAX_SKILL_FILE_BYTES = 2 * 1024 * 1024


def parse_skill_file(path: Path) -> SkillIR:
    """Parse a SKILL.md file into the project Skill IR."""
    source_path = Path(path)
    text = read_skill_text(source_path)
    return parse_skill_text(text, source_path=str(source_path))


def read_skill_text(path: Path) -> str:
    """Read one bounded local SKILL.md through the safe file boundary."""

    return _read_skill_file(Path(path))


def parse_skill_text(text: str, *, source_path: str = "SKILL.md") -> SkillIR:
    """Parse bounded in-memory SKILL.md text without reading a filesystem path."""

    if not isinstance(text, str):
        raise ValueError("SKILL.md text must be a string")
    if not isinstance(source_path, str) or not source_path:
        raise ValueError("SKILL.md source path must be a non-empty string")
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("SKILL.md text must be valid UTF-8") from error
    if len(encoded) > MAX_SKILL_FILE_BYTES:
        raise ValueError(f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes")
    metadata, body, body_start_line = _parse_frontmatter(text)
    body, input_schema = _extract_input_schema_declaration(body)
    checklist_details = _extract_ordered_step_details(body, body_start_line)
    checklist = [_format_step_detail(step) for step in checklist_details]
    sections = _parse_sections(body)
    declaration_lines = {
        step['line'] for step in checklist_details
        if isinstance(step.get('connector'), dict) and step['connector'].get('id') in {'http', 'http_assert'}
    }
    guidance_body = '\n'.join(
        re.sub(r'[ \t]+<!-- skill2workflow: (?:http|http_assert) \{.*\} -->[ \t]*$', '', line)
        if line_number in declaration_lines else line
        for line_number, line in enumerate(body.splitlines(), start=body_start_line)
    )

    ir = {
        "metadata": metadata,
        "description": metadata.get("description", ""),
        "hard_gates": _extract_hard_gates(guidance_body),
        "ordered_steps": checklist,
        "ordered_step_details": checklist_details,
        "tool_hints": _find_lines(guidance_body, ("tool", "command", "Run:", "Use ")),
        "human_gates": _find_lines(
            guidance_body,
            (
                "approval",
                "approve",
                "ask user",
                "human",
                "user review",
                "user reviews",
                "wait for user",
            ),
            skip_section_terms=("verification", "validation"),
        ),
        "verification_rules": _find_lines(guidance_body, ("verify", "test", "check", "validation")),
        "sections": sections,
        "source_path": source_path,
    }
    if input_schema is not None:
        ir['input_schema'] = input_schema
    return ir


def _extract_input_schema_declaration(body: str):
    """Remove one active data declaration without shifting any source lines."""
    lines = body.splitlines()
    schema = None
    fence_char, fence_length = '', 0
    for index, line in enumerate(lines):
        if fence_char:
            closing = re.match(r'^ {0,3}([`~]{3,})[ \t]*$', line)
            if closing and set(closing.group(1)) == {fence_char} and len(closing.group(1)) >= fence_length:
                fence_char = ''
            continue
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if opening and not (opening.group(1)[0] == '`' and '`' in opening.group(2)):
            fence_char, fence_length = opening.group(1)[0], len(opening.group(1))
            continue
        if not re.search(r'<!--\s*skill2workflow\s*:\s*input_schema\b', line, re.IGNORECASE):
            continue
        match = re.fullmatch(r' {0,3}<!-- skill2workflow: input_schema (\{.*\}) -->[ \t]*', line)
        try:
            if schema is not None or match is None:
                raise ValueError()
            payload = match.group(1)
            if len(payload.encode('utf-8')) > INPUT_SCHEMA_MAX_BYTES or '<!--' in payload or '-->' in payload:
                raise ValueError()
            schema = skill_input_schema_contract(load_assertion_json(payload))
        except (ValueError, TypeError, OverflowError, RecursionError) as error:
            raise ValueError(SKILL_INPUT_SCHEMA_ERROR) from error
        lines[index] = ''
    return ('\n'.join(lines), schema) if schema is not None else (body, None)


def _read_skill_file(path: Path) -> str:
    """Read one bounded SKILL.md without following path replacement races."""

    try:
        before = path.lstat()
    except OSError:
        raise
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("SKILL.md must be a regular non-symlink file")
    if before.st_size > MAX_SKILL_FILE_BYTES:
        raise ValueError(f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise ValueError("SKILL.md changed while being read")
        if opened.st_size > MAX_SKILL_FILE_BYTES:
            raise ValueError(f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes")
        chunks = []
        remaining = MAX_SKILL_FILE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_SKILL_FILE_BYTES:
            raise ValueError(f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes")
        after = path.lstat()
        if after.st_dev != before.st_dev or after.st_ino != before.st_ino:
            raise ValueError("SKILL.md changed while being read")
        if after.st_size > MAX_SKILL_FILE_BYTES:
            raise ValueError(f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes")
    finally:
        os.close(descriptor)
    return raw.decode("utf-8")


def _parse_frontmatter(text: str) -> Tuple[Dict[str, object], str, int]:
    return parse_frontmatter(text)


def _parse_sections(body: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current = "_root"
    sections[current] = []

    for line in body.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(2).strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return {title: "\n".join(lines).strip() for title, lines in sections.items()}


def _extract_hard_gates(body: str) -> List[str]:
    gates = []
    for match in re.finditer(r"<HARD-GATE>(.*?)</HARD-GATE>", body, flags=re.DOTALL | re.IGNORECASE):
        content = "\n".join(line.strip() for line in match.group(1).strip().splitlines())
        if content:
            gates.append(content)
    return gates


def _extract_ordered_step_details(body: str, start_line: int) -> List[Dict[str, object]]:
    checklist, has_checklist = _extract_checklist_details(body, start_line)
    steps = checklist if has_checklist else _extract_process_step_details(body, start_line)
    _apply_step_annotations(body, start_line, steps)
    return steps


def _apply_step_annotations(body: str, start_line: int, steps: List[Dict[str, object]]) -> None:
    selected = {step['line']: step for step in steps}
    fence_char = ''
    fence_length = 0
    for line_number, line in enumerate(body.splitlines(), start=start_line):
        if fence_char:
            closing = re.match(r'^ {0,3}([`~]{3,})[ \t]*$', line)
            if closing and set(closing.group(1)) == {fence_char} and len(closing.group(1)) >= fence_length:
                fence_char = ''
            continue
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if opening and not (opening.group(1)[0] == '`' and '`' in opening.group(2)):
            fence_char, fence_length = opening.group(1)[0], len(opening.group(1))
            continue
        reserved = re.findall(r'<!--\s*skill2workflow\b', line, re.IGNORECASE)
        if not reserved:
            continue
        annotation = re.search(r'[ \t]+<!-- skill2workflow: (human_gate|(?:http|http_assert) (\{.*\})) -->[ \t]*$', line)
        if len(reserved) != 1 or annotation is None or line_number not in selected:
            raise ValueError('Invalid Skill step annotation')
        content = re.sub(
            r'^\s*(?:[-*]\s+\[[ xX]\]\s+|\[[ xX]\]\s+|[-+*]\s+|\d+[.)]\s+)',
            '', line[:annotation.start()] + ' ', count=1,
        )
        title, detail = _split_step_title_detail(content)
        if not title:
            raise ValueError('Invalid Skill step annotation')
        selected[line_number].update(title=title, detail=detail)
        if annotation.group(1) == 'human_gate':
            selected[line_number]['node_type'] = 'human_gate'
        else:
            try:
                payload = annotation.group(2)
                if '<!--' in payload or '-->' in payload:
                    raise ValueError('nested comment delimiter')
                factory = skill_http_action_binding if annotation.group(1).startswith('http ') else skill_http_assertion_binding
                binding = factory(load_assertion_json(payload))
            except (ValueError, TypeError, RecursionError, OverflowError) as error:
                raise ValueError('Invalid Skill step annotation') from error
            selected[line_number].update(node_type='tool_call', connector=binding)
    # Legacy Checklist extraction has its own fence grammar. Never let a
    # declaration it extracted inside a fence fall through to keyword inference.
    for step in steps:
        if 'node_type' not in step and re.search(
            r'<!--\s*skill2workflow\b', str(step['title']) + str(step['detail']), re.IGNORECASE
        ):
            raise ValueError('Invalid Skill step annotation')


def _extract_checklist_details(
    body: str, start_line: int
) -> Tuple[List[Dict[str, object]], bool]:
    """Retain the legacy Checklist grammar, including empty-section precedence."""

    items: List[Dict[str, object]] = []
    current_section = "_root"
    in_fence = False
    has_checklist = False

    for line_number, raw_line in enumerate(body.splitlines(), start=start_line):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", raw_line)
        if heading:
            current_section = heading.group(2).strip()
            has_checklist = has_checklist or "checklist" in current_section.lower()
            continue

        if "checklist" not in current_section.lower():
            continue

        match = re.match(
            r"^\s*(?:[-*]\s+\[[ xX]\]\s+|\[[ xX]\]\s+|[-*]\s+|\d+[.)]\s+)(.+?)\s*$",
            raw_line,
        )
        if not match:
            continue

        title, detail = _split_step_title_detail(match.group(1))
        if title:
            items.append(
                {
                    "title": title,
                    "detail": detail,
                    "line": line_number,
                    "section": current_section,
                }
            )

    return items, has_checklist


def _extract_process_step_details(body: str, start_line: int) -> List[Dict[str, object]]:
    """Read one explicit numbered process without interpreting prose or examples."""

    sections = []
    current = None
    current_section = ""
    fence_char = ""
    fence_length = 0
    for line_number, raw_line in enumerate(body.splitlines(), start=start_line):
        if fence_char:
            closing = re.match(r"^ {0,3}([`~]{3,})[ \t]*$", raw_line)
            if (
                closing
                and set(closing.group(1)) == {fence_char}
                and len(closing.group(1)) >= fence_length
            ):
                fence_char = ""
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw_line)
        if opening and not (opening.group(1)[0] == "`" and "`" in opening.group(2)):
            fence_char = opening.group(1)[0]
            fence_length = len(opening.group(1))
            continue

        heading = re.match(r"^ {0,3}#{1,6}(?:[ \t]+(.*?))?[ \t]*$", raw_line)
        if heading:
            current_section = re.sub(r"[ \t]+#+[ \t]*$", "", heading.group(1) or "").strip()
            current = None
            if current_section.lower() in {"workflow", "steps"}:
                current = []
                sections.append(current)
            continue
        if current is None:
            continue
        # Include bullet markers when choosing the outer indentation, so a
        # numbered sublist under an unnumbered Notes item is never promoted.
        item = re.match(
            r"^( {0,3})(?:(\d+[.)])|[-+*])(?:[ \t]+(.*?))?[ \t]*$", raw_line
        )
        if item:
            current.append((
                len(item.group(1)), bool(item.group(2)), item.group(3) or "",
                line_number, current_section,
            ))

    populated = []
    for section in sections:
        if not section:
            continue
        outer_indent = min(item[0] for item in section)
        steps = []
        for indent, numbered, content, line_number, section_name in section:
            if not numbered or indent != outer_indent:
                continue
            title, detail = _split_step_title_detail(content)
            if title:
                steps.append({
                    "title": title, "detail": detail,
                    "line": line_number, "section": section_name,
                })
        if steps:
            populated.append(steps)
    if len(populated) > 1:
        raise ValueError(
            "SKILL.md has multiple Workflow or Steps sections; "
            "use one process section or an explicit Checklist"
        )
    return populated[0] if populated else []


def _clean_markdown_item(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\*\*(.+?)\*\*", r"\1", value)
    value = value.replace("**", "")
    return value.strip()


def _split_step_title_detail(value: str) -> Tuple[str, str]:
    value = value.strip()
    bold = re.match(r"^\*\*(.+?)\*\*\s*(?:[—-]\s*(.+))?$", value)
    if bold:
        return bold.group(1).strip(), (bold.group(2) or "").strip()

    cleaned = _clean_markdown_item(value)
    split = re.match(r"^(.+?)\s+[—-]\s+(.+)$", cleaned)
    if split:
        return split.group(1).strip(), split.group(2).strip()
    return cleaned, ""


def _format_step_detail(step: Dict[str, object]) -> str:
    title = str(step["title"])
    detail = str(step.get("detail") or "")
    if detail:
        return f"{title} — {detail}"
    return title


def _find_lines(
    body: str,
    needles: Tuple[str, ...],
    skip_section_terms: Tuple[str, ...] = (),
) -> List[str]:
    lowered_needles = tuple(needle.lower() for needle in needles)
    lowered_skip_sections = tuple(term.lower() for term in skip_section_terms)
    matches = []
    current_section = "_root"
    in_fence = False

    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", raw_line)
        if heading:
            current_section = heading.group(2).strip()
            continue
        if any(term in current_section.lower() for term in lowered_skip_sections):
            continue

        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        lowered = line.lower()
        if any(needle in lowered for needle in lowered_needles):
            matches.append(line)
    return matches
