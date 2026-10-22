#!/usr/bin/env python3
"""Check bounded repository documentation entrypoints without fetching URLs."""
import argparse
from collections import deque
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit


ENTRYPOINTS = ('README.md', 'docs/README.md', 'docs/reference.md')
LINK = re.compile(r'!?\[[^\]\n]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+["\'][^\n]*?["\'])?\)')


def visible_markdown(text):
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return '\n'.join(lines)


def anchors(text):
    result, used = set(), {}
    for line in visible_markdown(text).splitlines():
        heading = re.match(r'^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$', line)
        if not heading:
            continue
        title = heading.group(1).lower()
        slug = ''.join(character for character in title
                       if character in ' _-' or unicodedata.category(character)[0] in 'LN').replace(' ', '-')
        count = used.get(slug, 0)
        used[slug] = count + 1
        result.add(slug + ('-' + str(count) if count else ''))
    return result


def local_links(root, source):
    root = Path(root).resolve()
    source = Path(source)
    text = visible_markdown((root / source).read_text(encoding='utf-8'))
    targets = [match.group(1) or match.group(2) for match in LINK.finditer(text)]
    targets += re.findall(r'<(?:img|a)\b[^>]*\b(?:src|href)=["\']([^"\']+)["\']', text, re.I)
    for value in targets:
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            continue
        path = (root / source.parent / unquote(parsed.path)).resolve() if parsed.path else root / source
        try:
            relative = path.relative_to(root)
        except ValueError:
            yield None, unquote(parsed.fragment), 'outside_repository'
            continue
        if path.is_dir() and (path / 'README.md').is_file():
            relative = relative / 'README.md'
        yield relative, unquote(parsed.fragment), None


def check_links(root, source):
    errors = []
    root = Path(root)
    for target, fragment, error in local_links(root, source):
        if not error and not (root / target).exists():
            error = 'missing_target'
        if not error and fragment:
            if not (root / target).is_file() or (root / target).suffix != '.md':
                error = 'unsupported_anchor'
            elif fragment not in anchors((root / target).read_text(encoding='utf-8')):
                error = 'missing_anchor'
        if error:
            errors.append({'code': error, 'source': str(source), 'target': str(target) if target else None})
    return errors


def find_path(root, source, target, max_hops=3):
    root = Path(root)
    parsed = urlsplit(target)
    destination = Path(unquote(parsed.path))
    if parsed.fragment:
        path = root / destination
        if not path.is_file() or unquote(parsed.fragment) not in anchors(path.read_text(encoding='utf-8')):
            return None
    return _paths(root, source, max_hops).get(destination.as_posix())


def _paths(root, source, max_hops):
    queue, visited, paths = deque([(Path(source), (str(source),))]), set(), {}
    while queue:
        current, chain = queue.popleft()
        paths.setdefault(current.as_posix(), chain)
        if current in visited or len(chain) > max_hops or not (root / current).is_file() or current.suffix != '.md':
            continue
        visited.add(current)
        for linked, _fragment, error in local_links(root, current):
            if not error and linked is not None and (root / linked).exists():
                queue.append((linked, chain + (linked.as_posix(),)))
    return paths


def check_documentation(root):
    root = Path(root)
    errors = []
    for source in ENTRYPOINTS:
        if not (root / source).is_file():
            errors.append({'code': 'missing_entrypoint', 'source': source})
        else:
            errors.extend(check_links(root, Path(source)))
    readme_path = root / 'README.md'
    readme = readme_path.read_text(encoding='utf-8') if readme_path.is_file() else ''
    lines = len(readme.splitlines())
    if lines > 300:
        errors.append({'code': 'readme_line_budget', 'source': 'README.md'})
    hub = root / 'docs/README.md'
    if hub.is_file() and len(hub.read_text(encoding='utf-8').splitlines()) > 180:
        errors.append({'code': 'hub_line_budget', 'source': 'docs/README.md'})
    roadmap = readme.partition('## Roadmap\n')[2].split('\n## ', 1)[0]
    if not roadmap or len(roadmap.split()) > 100:
        errors.append({'code': 'roadmap_summary_budget', 'source': 'README.md'})
    guides = sorted(path.relative_to(root).as_posix() for path in (root / 'docs').glob('*.md'))
    reference = root / 'docs/reference.md'
    indexed = {target.as_posix() for target, _fragment, error in local_links(root, Path('docs/reference.md'))
               if target is not None and not error} if reference.is_file() else set()
    maximum = 0
    paths = _paths(root, 'README.md', 3)
    for guide in guides:
        if guide not in ('docs/README.md', 'docs/reference.md') and guide not in indexed:
            errors.append({'code': 'missing_reference_entry', 'source': guide})
        chain = paths.get(guide)
        if chain is None:
            errors.append({'code': 'unreachable_guide', 'source': guide})
        else:
            maximum = max(maximum, len(chain) - 1)
    return {'ok': not errors, 'readme_lines': lines, 'public_guides': len(guides),
            'max_guide_hops': maximum, 'errors': errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    report = check_documentation(parser.parse_args().root)
    print(json.dumps(report))
    raise SystemExit(0 if report['ok'] else 1)
