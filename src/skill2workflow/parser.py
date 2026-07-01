"""Parse standard SKILL.md files into a Skill IR."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


SkillIR = Dict[str, object]


def parse_skill_file(path: Path) -> SkillIR:
    """Parse a SKILL.md file into the project Skill IR."""
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8")
    metadata, body, body_start_line = _parse_frontmatter(text)
    checklist_details = _extract_checklist_details(body, body_start_line)
    checklist = [_format_step_detail(step) for step in checklist_details]
    sections = _parse_sections(body)

    return {
        "metadata": metadata,
        "description": metadata.get("description", ""),
        "hard_gates": _extract_hard_gates(body),
        "ordered_steps": checklist,
        "ordered_step_details": checklist_details,
        "tool_hints": _find_lines(body, ("tool", "command", "Run:", "Use ")),
        "human_gates": _find_lines(
            body,
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
        "verification_rules": _find_lines(body, ("verify", "test", "check", "validation")),
        "sections": sections,
        "source_path": str(source_path),
    }


def _parse_frontmatter(text: str) -> Tuple[Dict[str, str], str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, 1

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text, 1

    metadata: Dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")

    return metadata, "\n".join(lines[end_index + 1 :]), end_index + 2


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


def _extract_checklist_details(body: str, start_line: int) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    current_section = "_root"
    in_fence = False

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

    return items


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
