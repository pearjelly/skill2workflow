"""Bounded, non-executing SKILL frontmatter string projection, not full YAML."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple


ERROR = "Invalid SKILL.md frontmatter"
DIAGNOSTIC_VERSION = 'skill2workflow-skill-compile-diagnostic-0.1.0'
_DIAGNOSTIC_CODES = frozenset({'frontmatter_duplicate_key', 'frontmatter_invalid', 'frontmatter_unsupported'})
_BLOCK = re.compile(r'^([|>])([1-9][+-]?|[+-][1-9]?|)$')


class FrontmatterError(ValueError):
    """Keep the legacy message while carrying source-free diagnostic evidence."""

    def __init__(self, code: str, line=None):
        super().__init__(ERROR)
        self.code = code
        self.line = line


def skill_compile_diagnostic(error: Exception) -> Dict[str, object]:
    code, line = 'skill_invalid', None
    if isinstance(error, FrontmatterError) and type(error.code) is str and error.code in _DIAGNOSTIC_CODES:
        code = error.code
        if type(error.line) is int and 1 <= error.line <= 2 * 1024 * 1024 + 1:
            line = error.line
    return {'schema_version': DIAGNOSTIC_VERSION, 'code': code, 'line': line}


def format_frontmatter_error(error: FrontmatterError) -> str:
    diagnostic = skill_compile_diagnostic(error)
    location = ' near line ' + str(diagnostic['line']) if diagnostic['line'] is not None else ''
    if diagnostic['code'] == 'frontmatter_duplicate_key':
        return ERROR + '. A frontmatter field is repeated' + location + '. Keep one declaration per field.'
    if diagnostic['code'] == 'frontmatter_unsupported':
        return ERROR + '. Unsupported frontmatter form' + location + '. Use supported strings, | or > text blocks, or a flat metadata map.'
    return ERROR + '. Check frontmatter syntax' + location + ': quoting, indentation and supported text-block headers.'


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}, text, 1
    end = next((i for i in range(1, len(lines)) if re.fullmatch(r'---[ \t]*', lines[i])), None)
    if end is None:
        return {}, text, 1  # Preserve legacy incomplete-document behavior.
    header = lines[1:end]
    location = [2]
    try:
        first_index = next((i for i, line in enumerate(header) if line.strip() and not line.lstrip().startswith('#')), None)
        first = header[first_index] if first_index is not None else ''
        location[0] = first_index + 2 if first_index is not None else 2
        metadata, index = _mapping(header, 0, _indent(first), nested=False, location=location)
        if index != len(header):
            raise ValueError(ERROR)
    except FrontmatterError as error:
        raise FrontmatterError(error.code, error.line if error.line is not None else location[0]) from error
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError) as error:
        raise FrontmatterError('frontmatter_invalid', location[0]) from error
    return metadata, '\n'.join(lines[end + 1:]), end + 2


def _indent(line: str) -> int:
    prefix = line[:len(line) - len(line.lstrip(' \t'))]
    if '\t' in prefix:
        raise ValueError(ERROR)
    return len(prefix)


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('#'):
        return ''
    if raw.startswith('"'):
        value, end = json.JSONDecoder().raw_decode(raw)
        tail = raw[end:]
        if not isinstance(value, str) or tail and not re.fullmatch(r'[ \t]+(?:#.*)?', tail):
            raise ValueError(ERROR)
    elif raw.startswith("'"):
        match = re.fullmatch(r"'((?:[^']|'')*)'(?:[ \t]+(?:#.*)?)?", raw)
        if not match:
            raise ValueError(ERROR)
        value = match.group(1).replace("''", "'")
    else:
        value = _uncomment(raw)
        if value in {'-', '?', ':'} or value.startswith(('*', '&', '!', '{', '}', '[', ']', '|', '>', '%', '@', '`', '- ', '? ', ': ')) or re.search(r':[ \t]', value):
            raise FrontmatterError('frontmatter_unsupported')
    value.encode('utf-8')
    return value


def _uncomment(raw: str) -> str:
    for index, char in enumerate(raw):
        if char == '#' and (index == 0 or raw[index - 1] in ' \t'):
            return raw[:index].rstrip()
    return raw.rstrip()


def _entry(line: str) -> Tuple[str, str]:
    """Find one key separator in linear work, never regex-backtrack over padding."""
    if line.startswith('"'):
        _, end = json.JSONDecoder().raw_decode(line)
    elif line.startswith("'"):
        end = 1
        while end < len(line):
            if line[end] == "'":
                if end + 1 < len(line) and line[end + 1] == "'":
                    end += 2
                    continue
                end += 1
                break
            end += 1
    else:
        end = next((i for i, char in enumerate(line) if char == ':' and (i + 1 == len(line) or line[i + 1] in ' \t')), -1)
        if end < 0:
            raise ValueError(ERROR)
    key = _scalar(line[:end])
    tail = line[end:].lstrip(' \t')
    if not tail.startswith(':') or len(tail) > 1 and tail[1] not in ' \t':
        raise ValueError(ERROR)
    return key, tail[1:].strip()


def _mapping(lines: List[str], index: int, indent: int, *, nested: bool, location: List[int]) -> Tuple[Dict[str, object], int]:
    result: Dict[str, object] = {}
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith('#'):
            index += 1
            continue
        location[0] = index + 2
        level = _indent(line)
        if level < indent:
            break
        if level != indent:
            raise ValueError(ERROR)
        key, raw = _entry(line[level:])
        if not key:
            raise ValueError(ERROR)
        if key == '<<':
            raise FrontmatterError('frontmatter_unsupported')
        if key in result:
            raise FrontmatterError('frontmatter_duplicate_key')
        index += 1
        header = _uncomment(raw)
        if key == 'metadata' and not nested:
            if re.fullmatch(r'\{[ \t]*\}', header):
                result[key] = {}
                continue
            if raw and not raw.startswith('#'):
                raise FrontmatterError('frontmatter_unsupported')
            child = next((i for i in range(index, len(lines)) if lines[i].strip() and not lines[i].lstrip().startswith('#')), len(lines))
            if child < len(lines) and _indent(lines[child]) > indent:
                result[key], index = _mapping(lines, index, _indent(lines[child]), nested=True, location=location)
            else:
                result[key] = {}
            continue
        if header.startswith(('|', '>')):
            block = _BLOCK.fullmatch(header)
            if not block:
                raise ValueError(ERROR)
            value, index = _block(lines, index, indent, block.group(1), block.group(2))
        else:
            value = _scalar(raw)
        result[key] = value
    return result, index


def _ordinary(line: str) -> bool:
    return bool(line) and not line.startswith((' ', '\t'))


def _block(lines: List[str], index: int, parent: int, style: str, modifiers: str) -> Tuple[str, int]:
    start = index
    while index < len(lines) and (not lines[index].strip() or _indent(lines[index]) > parent):
        index += 1
    content = lines[start:index]
    nonempty = [line for line in content if line.strip()]
    indicator = next((int(char) for char in modifiers if char.isdigit()), None)
    indent = parent + indicator if indicator else (_indent(nonempty[0]) if nonempty else max([parent + 1] + [len(line) for line in content]))
    if any(_indent(line) < indent for line in nonempty):
        raise ValueError(ERROR)
    first_text = next((i for i, line in enumerate(content) if line.strip()), len(content))
    if indicator is None and nonempty and any(len(line) > indent for line in content[:first_text]):
        raise ValueError(ERROR)
    values = [line[indent:] for line in content]
    output = []
    previous_text = None
    for offset, line in enumerate(values):
        output.append(line)
        separator = '\n'
        if style == '>' and offset + 1 < len(values):
            following = values[offset + 1]
            if _ordinary(line) and _ordinary(following):
                separator = ' '
            elif not line and _ordinary(following) and previous_text is not None and _ordinary(previous_text):
                separator = ''
        output.append(separator)
        if line:
            previous_text = line
    value = ''.join(output)
    if '-' in modifiers:
        value = value.rstrip('\n')
    elif '+' not in modifiers:
        value = value.rstrip('\n') + ('\n' if any(values) else '')
    return value, index
