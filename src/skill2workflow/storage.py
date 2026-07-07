"""Local persistence backends."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Dict, List


RunState = Dict[str, object]
WorkflowRecord = Dict[str, object]
AuditEvent = Dict[str, object]


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

        with self._connection() as connection:
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
        with self._connection() as connection:
            row = connection.execute("select state_json from runs where run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise FileNotFoundError(f"run not found: {run_id}")
        return json.loads(str(row[0]))

    def list(self) -> List[RunState]:
        with self._connection() as connection:
            rows = connection.execute("select state_json from runs order by run_id").fetchall()
        return [json.loads(str(row[0])) for row in rows]

    def _initialize(self) -> None:
        with self._connection() as connection:
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

    def _connection(self):
        return _sqlite_connection(self.db_path)


def create_run_store(state_dir: Path, storage: str):
    if storage == "json":
        return JsonRunStore(state_dir)
    if storage == "sqlite":
        return SqliteRunStore(state_dir)
    raise ValueError(f"unsupported run storage: {storage}")


class JsonControlStore:
    """Persist control-plane registry and audit metadata as JSON files."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.workflows_dir = self.state_dir / "workflows"
        self.index_path = self.workflows_dir / "index.json"
        self.audit_path = self.state_dir / "audit.log.jsonl"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def load_index(self) -> Dict[str, WorkflowRecord]:
        if not self.index_path.exists():
            return {}
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        if not isinstance(index, dict):
            raise ValueError("workflow index must be an object")
        return index

    def save_index(self, index: Dict[str, WorkflowRecord]) -> None:
        self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_audit(self, event: AuditEvent) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def list_audit_events(self) -> List[AuditEvent]:
        if not self.audit_path.exists():
            return []
        events = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events


class SqliteControlStore:
    """Persist workflow registry and audit metadata in SQLite."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.workflows_dir = self.state_dir / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.workflows_dir / "index.json"
        self.audit_path = self.state_dir / "audit.log.jsonl"
        self.db_path = self.state_dir / "control.sqlite3"
        self._initialize()
        self._import_json_state()

    def load_index(self) -> Dict[str, WorkflowRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "select record_key, record_json from workflow_versions order by record_key"
            ).fetchall()
        return {str(row[0]): json.loads(str(row[1])) for row in rows}

    def save_index(self, index: Dict[str, WorkflowRecord]) -> None:
        with self._connection() as connection:
            connection.execute("delete from workflow_versions")
            connection.executemany(
                """
                insert into workflow_versions (
                    record_key,
                    workflow_id,
                    name,
                    version,
                    status,
                    checksum,
                    artifact,
                    published_at,
                    deprecated_at,
                    record_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        key,
                        str(record.get("workflow_id", "")),
                        str(record.get("name", "")),
                        str(record.get("version", "")),
                        str(record.get("status", "")),
                        str(record.get("checksum", "")),
                        str(record.get("artifact", "")),
                        str(record.get("published_at", "")),
                        str(record.get("deprecated_at", "")),
                        json.dumps(record, ensure_ascii=False, sort_keys=True),
                    )
                    for key, record in index.items()
                ],
            )

    def append_audit(self, event: AuditEvent) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                insert into audit_events (
                    event_type,
                    workflow_id,
                    workflow_version,
                    run_id,
                    timestamp,
                    payload_json
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    _event_value(event, "type", "event"),
                    _event_value(event, "workflow_id", ""),
                    _event_value(event, "workflow_version", ""),
                    _event_value(event, "run_id", ""),
                    _event_value(event, "timestamp", ""),
                    json.dumps(event, ensure_ascii=False, sort_keys=True),
                ),
            )

    def list_audit_events(self) -> List[AuditEvent]:
        with self._connection() as connection:
            rows = connection.execute("select payload_json from audit_events order by sequence").fetchall()
        return [json.loads(str(row[0])) for row in rows]

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                create table if not exists workflow_versions (
                    record_key text primary key,
                    workflow_id text not null,
                    name text not null,
                    version text not null,
                    status text not null,
                    checksum text not null,
                    artifact text not null,
                    published_at text not null,
                    deprecated_at text not null,
                    record_json text not null
                )
                """
            )
            connection.execute(
                """
                create table if not exists audit_events (
                    sequence integer primary key autoincrement,
                    event_type text not null,
                    workflow_id text not null,
                    workflow_version text not null,
                    run_id text not null,
                    timestamp text not null,
                    payload_json text not null
                )
                """
            )

    def _import_json_state(self) -> None:
        if self.index_path.exists() and not self.load_index():
            index = json.loads(self.index_path.read_text(encoding="utf-8"))
            if isinstance(index, dict):
                self.save_index(index)

        if self.audit_path.exists() and not self.list_audit_events():
            for line in self.audit_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    event = json.loads(line)
                    if isinstance(event, dict):
                        self.append_audit(event)

    def _connection(self):
        return _sqlite_connection(self.db_path)


def create_control_store(state_dir: Path, storage: str):
    if storage == "json":
        return JsonControlStore(state_dir)
    if storage == "sqlite":
        return SqliteControlStore(state_dir)
    raise ValueError(f"unsupported control storage: {storage}")


@contextmanager
def _sqlite_connection(db_path: Path):
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            yield connection


def _event_value(event: Dict[str, object], key: str, default: str) -> str:
    value = event.get(key, default)
    return str(value) if value is not None else default
