"""Documentation assertions follow real links, not duplicated README prose."""
from pathlib import Path

from scripts.documentation_check import find_path


ROOT = Path(__file__).resolve().parents[1]


def assert_guide_reachable(case, target):
    route = find_path(ROOT, 'README.md', target, 3)
    case.assertIsNotNone(route, 'No public documentation path to ' + target)
