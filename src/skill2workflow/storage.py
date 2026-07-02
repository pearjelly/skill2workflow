"""Run-state storage backends for the local executor."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List


RunState = Dict[str, object]


class JsonRunStore:
    """Persist run state as one JSON file per run."""

    def __init__(self, state_dir: Path):
        self.runs_dir = Path(state_dir) / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: RunState) -> None:
        path = self.runs_dir / f"{state['run_id']}.json"
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, run_id: str) -> RunState:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"run not found: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> List[RunState]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.runs_dir.glob("*.json"))]


class SqliteRunStore:
    """Persist run state and queryable run events in SQLite."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "runs.sqlite3"
        self._initialize()

    def save(self, state: RunState) -> None:
        payload = json.dumps(state, ensure_ascii=False, sort_keys=True)
        events = state.get("events", [])
        if not isinstance(events, list):
            events = []

        with self._connect() as connection:
            connection.execute(
                """
                insert into runs (
                    run_id,
                    workflow_id,
                    workflow_version,
                    status,
                    current_node,
                    state_json,
                    updated_at
                )
                values (?, ?, ?, ?, ?, ?, datetime('now'))
                on conflict(run_id) do update set
                    workflow_id = excluded.workflow_id,
                    workflow_version = excluded.workflow_version,
                    status = excluded.status,
                    current_node = excluded.current_node,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state["run_id"],
                    state.get("workflow_id", "workflow"),
                    state.get("workflow_version", "0.1.0"),
                    state.get("status", "created"),
                    state.get("current_node", ""),
                    payload,
                ),
            )
            connection.execute("delete from run_events where run_id = ?", (state["run_id"],))
            connection.executemany(
                """
                insert into run_events (
                    run_id,
                    sequence,
                    event_type,
                    node_id,
                    timestamp,
                    payload_json
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        state["run_id"],
                        index,
                        _event_value(event, "type", "event"),
                        _event_value(event, "node_id", ""),
                        _event_value(event, "timestamp", ""),
                        json.dumps(event, ensure_ascii=False, sort_keys=True),
                    )
                    for index, event in enumerate(events, start=1)
                    if isinstance(event, dict)
                ],
            )

    def load(self, run_id: str) -> RunState:
        with self._connect() as connection:
            row = connection.execute("select state_json from runs where run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise FileNotFoundError(f"run not found: {run_id}")
        return json.loads(str(row[0]))

    def list(self) -> List[RunState]:
        with self._connect() as connection:
            rows = connection.execute("select state_json from runs order by run_id").fetchall()
        return [json.loads(str(row[0])) for row in rows]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists runs (
                    run_id text primary key,
                    workflow_id text not null,
                    workflow_version text not null,
                    status text not null,
                    current_node text not null,
                    state_json text not null,
                    updated_at text not null
                )
                """
            )
            connection.execute(
                """
                create table if not exists run_events (
                    run_id text not null,
                    sequence integer not null,
                    event_type text not null,
                    node_id text not null,
                    timestamp text not null,
                    payload_json text not null,
                    primary key (run_id, sequence),
                    foreign key (run_id) references runs(run_id) on delete cascade
                )
                """
            )

    def _connect(self):
        return sqlite3.connect(self.db_path)


def create_run_store(state_dir: Path, storage: str):
    if storage == "json":
        return JsonRunStore(state_dir)
    if storage == "sqlite":
        return SqliteRunStore(state_dir)
    raise ValueError(f"unsupported run storage: {storage}")


def _event_value(event: Dict[str, object], key: str, default: str) -> str:
    value = event.get(key, default)
    return str(value) if value is not None else default
