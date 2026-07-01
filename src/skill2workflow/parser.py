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
    metadata, body = _parse_frontmatter(text)
    sections = _parse_sections(body)
    checklist = _extract_checklist(sections)

    return {
        "metadata": metadata,
        "description": metadata.get("description", ""),
        "hard_gates": _extract_hard_gates(body),
        "ordered_steps": checklist,
        "tool_hints": _find_lines(body, ("tool", "command", "Run:", "Use ")),
        "human_gates": _find_lines(body, ("approval", "approve", "review", "wait for user", "human")),
        "verification_rules": _find_lines(body, ("verify", "test", "check", "validation")),
        "sections": sections,
        "source_path": str(source_path),
    }


def _parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    metadata: Dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")

    return metadata, "\n".join(lines[end_index + 1 :])


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


def _extract_checklist(sections: Dict[str, str]) -> List[str]:
    checklist_text = ""
    for title, content in sections.items():
        if "checklist" in title.lower():
            checklist_text = content
            break

    if not checklist_text:
        return []

    items = []
    for line in checklist_text.splitlines():
        match = re.match(r"^\s*(?:[-*]\s+|\d+[.)]\s+|\[[ xX]\]\s+)(.+?)\s*$", line)
        if not match:
            continue
        item = _clean_markdown_item(match.group(1))
        if item:
            items.append(item)
    return items


def _clean_markdown_item(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\*\*(.+?)\*\*", r"\1", value)
    value = value.replace("**", "")
    return value.strip()


def _find_lines(body: str, needles: Tuple[str, ...]) -> List[str]:
    lowered_needles = tuple(needle.lower() for needle in needles)
    matches = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        lowered = line.lower()
        if any(needle in lowered for needle in lowered_needles):
            matches.append(line)
    return matches
