import json
from pathlib import Path
from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow_structured
from skill2workflow.parser import parse_skill_file
from skill2workflow.visualizer import workflow_to_litegraph


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SKILLS = ROOT / "examples" / "skills"
EXAMPLE_WORKFLOWS = ROOT / "examples" / "workflows"
REQUIRED_ENTERPRISE_SCENARIOS = {
    "sales-follow-up",
    "customer-service-escalation",
    "risk-review",
    "operations-analysis",
}


class ExampleFixtureTests(TestCase):
    def test_enterprise_example_pack_contains_required_scenarios(self):
        scenario_names = {path.parent.name for path in EXAMPLE_SKILLS.glob("*/SKILL.md")}
        missing = sorted(REQUIRED_ENTERPRISE_SCENARIOS - scenario_names)

        self.assertEqual(missing, [])

    def test_example_skills_compile_to_committed_workflow_fixtures(self):
        skill_paths = sorted(EXAMPLE_SKILLS.glob("*/SKILL.md"))

        self.assertGreaterEqual(len(skill_paths), len(REQUIRED_ENTERPRISE_SCENARIOS))
        for skill_path in skill_paths:
            scenario = skill_path.parent.name
            fixture_path = EXAMPLE_WORKFLOWS / f"{scenario}.workflow.json"
            with self.subTest(scenario=scenario):
                self.assertTrue(fixture_path.exists(), f"{fixture_path} is missing")
                compiled = compile_ir_to_workflow(parse_skill_file(skill_path.relative_to(ROOT)))
                committed = _load_json(fixture_path)
                self.assertEqual(validate_workflow_structured(compiled), [])
                self.assertEqual(compiled, committed)

    def test_example_workflows_have_matching_litegraph_fixtures(self):
        workflow_paths = sorted(EXAMPLE_WORKFLOWS.glob("*.workflow.json"))

        self.assertGreaterEqual(len(workflow_paths), len(REQUIRED_ENTERPRISE_SCENARIOS))
        for workflow_path in workflow_paths:
            graph_path = workflow_path.with_suffix("").with_suffix(".litegraph.json")
            with self.subTest(workflow=workflow_path.name):
                self.assertTrue(graph_path.exists(), f"{graph_path} is missing")
                workflow = _load_json(workflow_path)
                expected_graph = workflow_to_litegraph(workflow)
                committed_graph = _load_json(graph_path)
                self.assertEqual(expected_graph, committed_graph)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
