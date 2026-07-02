"""Durable local Workflow DSL executor."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .storage import create_run_store


RunState = Dict[str, object]


class LocalExecutor:
    """Execute Workflow DSL with pluggable local run-state storage."""

    def __init__(self, state_dir: Path, storage: str = "json"):
        self.state_dir = Path(state_dir)
        self.store = create_run_store(self.state_dir, storage)

    def run(self, workflow: Dict[str, object]) -> RunState:
        workflow_meta = workflow.get("workflow", {})
        if not isinstance(workflow_meta, dict):
            workflow_meta = {}

        state: RunState = {
            "run_id": f"run_{uuid.uuid4().hex[:12]}",
            "workflow_id": workflow_meta.get("id", "workflow"),
            "workflow_version": workflow_meta.get("version", "0.1.0"),
            "status": "created",
            "current_node": workflow.get("entry", "start"),
            "context": {},
            "node_results": {},
            "events": [],
            "workflow": workflow,
        }
        self._save(state)
        return self._drive(state)

    def resume(self, run_id: str, approved: bool = True) -> RunState:
        state = self._load(run_id)
        if state["status"] != "waiting":
            raise ValueError(f"run {run_id} is not waiting")

        workflow = state["workflow"]
        node = self._node_map(workflow)[state["current_node"]]
        next_node = node.get("on_success") if approved else node.get("on_failure")
        if not isinstance(next_node, str):
            raise ValueError(f"run {run_id} cannot resume from {node['id']}")

        state["node_results"][node["id"]] = {
            "status": "approved" if approved else "rejected",
            "title": node.get("title", node["id"]),
            "approved": approved,
            "timestamp": _now(),
        }
        state["events"].append(
            {
                "type": "human_gate_resumed",
                "node_id": node["id"],
                "approved": approved,
                "timestamp": _now(),
            }
        )
        state["status"] = "running"
        state["current_node"] = next_node
        self._save(state)
        return self._drive(state)

    def list_runs(self) -> List[RunState]:
        return [_summarize_run(state) for state in self.store.list()]

    def get_run(self, run_id: str) -> RunState:
        return self._load(run_id)

    def _drive(self, state: RunState) -> RunState:
        workflow = state["workflow"]
        node_map = self._node_map(workflow)
        state["status"] = "running"

        for _ in range(len(node_map) + 1):
            current_id = state["current_node"]
            node = node_map[current_id]
            node_type = node.get("type")

            if node_type == "end":
                state["status"] = "completed"
                state["node_results"][current_id] = {
                    "status": "completed",
                    "title": node.get("title", current_id),
                    "timestamp": _now(),
                }
                self._event(state, "run_completed", current_id)
                self._save(state)
                return state

            if node_type == "failure":
                state["status"] = "failed"
                state["node_results"][current_id] = {
                    "status": "failed",
                    "title": node.get("title", current_id),
                    "timestamp": _now(),
                }
                self._event(state, "run_failed", current_id)
                self._save(state)
                return state

            if node_type == "human_gate":
                state["status"] = "waiting"
                self._event(state, "human_gate_waiting", current_id)
                self._save(state)
                return state

            self._event(state, "node_started", current_id)
            state["node_results"][current_id] = {
                "status": "completed",
                "title": node.get("title", current_id),
                "timestamp": _now(),
            }
            self._event(state, "node_completed", current_id)

            next_node = node.get("on_success")
            if not isinstance(next_node, str) or next_node not in node_map:
                state["status"] = "failed"
                state["error"] = f"{current_id} has no valid on_success target"
                self._event(state, "run_failed", current_id)
                self._save(state)
                return state

            state["current_node"] = next_node
            self._save(state)

        state["status"] = "failed"
        state["error"] = "execution exceeded workflow node count"
        self._save(state)
        return state

    def _event(self, state: RunState, event_type: str, node_id: str) -> None:
        state["events"].append(
            {
                "type": event_type,
                "node_id": node_id,
                "timestamp": _now(),
            }
        )

    def _save(self, state: RunState) -> None:
        self.store.save(state)

    def _load(self, run_id: str) -> RunState:
        return self.store.load(run_id)

    @staticmethod
    def _node_map(workflow: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        return {node["id"]: node for node in workflow.get("nodes", [])}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summarize_run(state: RunState) -> RunState:
    return {
        "run_id": state["run_id"],
        "workflow_id": state["workflow_id"],
        "workflow_version": state["workflow_version"],
        "status": state["status"],
        "current_node": state["current_node"],
        "event_count": len(state.get("events", [])),
        "node_result_count": len(state.get("node_results", {})),
    }
