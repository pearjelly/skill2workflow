"""Documentation assertions follow real links, not duplicated README prose."""
from pathlib import Path

from scripts.documentation_check import find_path


ROOT = Path(__file__).resolve().parents[1]


def assert_guide_reachable(case, target):
    route = find_path(ROOT, 'README.md', target, 3)
    case.assertIsNotNone(route, 'No public documentation path to ' + target)


def read_api_section(section):
    """Read one preserved API contract, keeping assertions scoped to a resource."""
    text = (ROOT / 'docs/api-reference.md').read_text(encoding='utf-8')
    return text.split('<a id="' + section + '"></a>', 1)[1].split('<!-- end: ' + section + ' -->', 1)[0]
