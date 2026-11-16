"""Shared typed JSON contracts for ingestion, execution and persistence.

Optional fields preserve the existing additive DSL/state format. Extension
maps are JSON dictionaries; core container and identity fields are typed.
These annotations do not replace runtime validation or introduce dependencies.
"""

from typing import Any, Dict, List, TypedDict

JSONMap = Dict[str, Any]


class SkillIR(TypedDict, total=False):
    metadata: JSONMap
    description: str
    hard_gates: List[str]
    ordered_steps: List[str]
    ordered_step_details: List[JSONMap]
    tool_hints: List[str]
    human_gates: List[str]
    verification_rules: List[str]
    sections: Dict[str, str]
    source_path: str
    input_schema: JSONMap
    workflow_version: str


class WorkflowMetadata(TypedDict, total=False):
    id: str
    name: str
    description: str
    version: str
    status: str


class Workflow(TypedDict, total=False):
    schema_version: str
    workflow: WorkflowMetadata
    entry: str
    nodes: List[JSONMap]
    edges: List[JSONMap]
    input_schema: JSONMap
    state_schema: JSONMap
    guards: List[JSONMap]
    checkpoints: List[JSONMap]
    policies: JSONMap


class RunState(TypedDict, total=False):
    run_id: str
    workflow_id: str
    workflow_version: str
    status: str
    current_node: str
    context: JSONMap
    node_results: Dict[str, JSONMap]
    events: List[JSONMap]
    workflow: Workflow
    execution: JSONMap
    error: str
    error_code: str
    event_count: int
    node_result_count: int
    created_at: str
    updated_at: str
