"""Local persistence backends."""

from __future__ import annotations

import hashlib
import heapq
import json
import os
import sqlite3
import stat
from collections import Counter, deque
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .artifact_io import read_workflow_artifact
from .state_layout import ensure_current_state_layout


RunState = Dict[str, object]
WorkflowRecord = Dict[str, object]
AuditEvent = Dict[str, object]


AUDIT_INTEGRITY_SCHEMA_VERSION = "skill2workflow-audit-integrity-0.1.0"
AUDIT_INTEGRITY_ALGORITHM = "sha256-chain-v1"
MAX_AUDIT_LIST_ITEMS = 1000
MAX_RUN_LIST_ITEMS = 1000
MAX_INTERRUPTED_RECOVERY_BATCH = 100
MAX_JSON_RUN_STATE_BYTES = 8 * 1024 * 1024
# Keep the SQLite run document on the same fixed persistence boundary as the
# dependency-light JSON backend.  SQLite is the production path, so it must
# not become an unbounded escape hatch for workflow/context/result state.
MAX_SQLITE_RUN_STATE_BYTES = MAX_JSON_RUN_STATE_BYTES
MAX_JSON_CONTROL_INDEX_BYTES = 8 * 1024 * 1024
# A registry row carries only published-version metadata, but it is still a
# durable SQLite document. Keep one row below the published-artifact ceiling so
# metadata cannot become an unbounded side channel or a decode-time allocation.
MAX_SQLITE_WORKFLOW_RECORD_BYTES = 2 * 1024 * 1024
# Trigger responses are compact replay metadata, never the trigger input or
# provider payload. Keep the SQLite idempotency ledger on a small fixed UTF-8
# envelope so completed rows cannot become an unbounded control-plane sink.
MAX_SQLITE_TRIGGER_RESPONSE_BYTES = 64 * 1024
# Audit events are compact metadata by contract. Keep both local backends on
# one fixed UTF-8 envelope so JSONL and SQLite cannot become unbounded sinks.
MAX_AUDIT_EVENT_BYTES = 1 * 1024 * 1024
_JSON_RUN_STATE_READ_CHUNK_BYTES = 64 * 1024
_AUDIT_GENESIS_DIGEST = ""
_LEGACY_AUDIT_COLUMNS = {
    "sequence",
    "event_type",
    "workflow_id",
    "workflow_version",
    "run_id",
    "timestamp",
    "payload_json",
}
_CURRENT_AUDIT_COLUMNS = _LEGACY_AUDIT_COLUMNS | {"prev_digest", "digest"}


class ExecutionFencedError(ValueError):
    """Raised when an obsolete runtime owner attempts to mutate a recovered run."""


def _validate_audit_event_limit(limit: object) -> None:
    if limit is None:
        return
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 1
        or limit > MAX_AUDIT_LIST_ITEMS
    ):
        raise ValueError(
            f"audit event limit must be an integer from 1 to {MAX_AUDIT_LIST_ITEMS}"
        )


def _audit_event_matches(
    event: object,
    *,
    workflow_id: str = "",
    version: str = "",
    run_id: str = "",
    event_type: str = "",
) -> bool:
    if not isinstance(event, dict):
        return not any((workflow_id, version, run_id, event_type))
    return not any(
        (
            workflow_id and str(event.get("workflow_id", "")) != workflow_id,
            version and str(event.get("workflow_version", "")) != version,
            run_id and str(event.get("run_id", "")) != run_id,
            event_type and str(event.get("type", "")) != event_type,
        )
    )


class JsonRunStore:
    """Persist run state as one JSON file per run."""

    def __init__(self, state_dir: Path):
        self.runs_dir = Path(state_dir) / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: RunState) -> None:
        path = self.runs_dir / f"{state['run_id']}.json"
        path.write_bytes(_encode_json_run_state(state))

    def load(self, run_id: str) -> RunState:
        path = self.runs_dir / f"{run_id}.json"
        try:
            return _read_json_run_state(path)
        except FileNotFoundError as error:
            raise FileNotFoundError(f"run not found: {run_id}") from error

    def get_run_summary(self, run_id: str) -> RunState:
        return _summarize_run_document(self.load(run_id))

    def count(self) -> int:
        """Count persisted run documents without loading their contents."""

        return sum(1 for path in self.runs_dir.glob("*.json") if path.is_file())

    def list(self) -> List[RunState]:
        return [_read_json_run_state(path) for path in sorted(self.runs_dir.glob("*.json"))]

    def run_event_type_counts(self, run_ids: List[str]) -> Dict[str, Dict[str, int]]:
        selected = {str(run_id) for run_id in run_ids if str(run_id)}
        counts = {}
        if not selected:
            return counts
        for state in self.list():
            run_id = str(state.get("run_id", ""))
            if run_id not in selected:
                continue
            counter = Counter()
            events = state.get("events", [])
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict):
                        counter[str(event.get("type", "event"))] += 1
            counts[run_id] = dict(counter)
        return counts

    def list_bounded(self, limit: int) -> List[RunState]:
        """Read only the newest bounded run summaries' source states."""

        _validate_run_list_limit(limit)
        return self._bounded_items(limit)[0]

    def snapshot_window(self, limit: int) -> Dict[str, object]:
        """Read a bounded run tail while retaining aggregate status counts."""

        _validate_snapshot_limit(limit)
        status_counts = Counter()
        items, total = self._bounded_items(limit, status_counts=status_counts)
        return {
            "total": total,
            "status_counts": dict(status_counts),
            "items": items,
        }

    def _bounded_items(self, limit: int, status_counts=None):
        selected = []
        total = 0
        for path in self.runs_dir.glob("*.json"):
            state = _read_json_run_state(path)
            total += 1
            if status_counts is not None:
                status_counts[str(state.get("status", "other"))] += 1
            key = _json_run_sort_key(state, path)
            item = (key, state)
            if len(selected) < limit:
                heapq.heappush(selected, item)
            elif key > selected[0][0]:
                heapq.heapreplace(selected, item)
        return [state for _, state in sorted(selected, key=lambda item: item[0])], total

    def start_execution(self, state: RunState, owner_id: str, execution_id: str) -> None:
        self.save(state)

    def claim_execution(self, run_id: str, owner_id: str, execution_id: str) -> None:
        return

    def save_execution(
        self, state: RunState, owner_id: str, execution_id: str
    ) -> None:
        self.save(state)

    def ensure_execution_active(
        self, run_id: str, owner_id: str, execution_id: str
    ) -> None:
        return

    def recover_interrupted(self, current_owner: str, max_items: int = None) -> List[RunState]:
        raise ValueError("interrupted run recovery requires sqlite storage")

    def recover_interrupted_batch(
        self, current_owner: str, max_items: int
    ) -> Tuple[List[RunState], int]:
        raise ValueError("interrupted run recovery requires sqlite storage")

    def iter_interrupted_runs(self, after_run_id: str = ""):
        """Stream interrupted run states in stable, cursor-friendly order."""

        for path in sorted(self.runs_dir.glob("*.json")):
            if not path.is_file():
                continue
            state = _read_json_run_state(path)
            run_id = str(state.get("run_id", ""))
            if (
                str(state.get("status", "")) == "interrupted"
                and (not after_run_id or run_id > str(after_run_id))
            ):
                yield state

    def expire_waiting_workflow_deadlines(
        self, now: str, limit: int = 256
    ) -> List[RunState]:
        """Expire bounded waiting runs whose durable workflow deadline elapsed."""

        _validate_sweep_limit(limit)
        expired = []
        for state in self.list():
            if len(expired) >= limit:
                break
            updated = _expire_waiting_workflow_state(state, now)
            if updated is None:
                continue
            self.save(updated)
            expired.append(updated)
        return expired

    def list_workflow_timeout_runs(self, limit: int = 256) -> List[RunState]:
        """Return a bounded set of terminal workflow-timeout states."""

        _validate_sweep_limit(limit)
        return [
            state
            for state in self.list()
            if str(state.get("status", "")) == "failed"
            and str(state.get("error_code", "")) == "workflow_timeout"
        ][:limit]

    def run_page(
        self,
        limit: int,
        *,
        before_updated_at: str = "",
        before_run_id: str = "",
        status: str = "",
        workflow_id: str = "",
    ) -> Dict[str, object]:
        """Return one bounded filtered page from the SQLite run index."""

        raise ValueError("run pages require sqlite storage")

    def request_cancellation(self, run_id: str):
        state = self.load(run_id)
        status = str(state.get("status", ""))
        if status == "cancelled":
            return state, False
        if status in {"completed", "failed", "interrupted"}:
            raise ValueError(f"run {run_id} is already {status}")
        marker = self.runs_dir / f"{run_id}.cancel"
        newly_requested = False
        try:
            with marker.open("x", encoding="utf-8") as handle:
                handle.write(_utc_now())
            marker.chmod(0o600)
            newly_requested = True
        except FileExistsError:
            pass
        except OSError as error:
            raise ValueError(f"run {run_id} cancellation could not be recorded") from error
        if status == "waiting":
            state = _cancel_state(state)
            self.save(state)
        else:
            state = dict(state)
            state["status"] = "cancel_requested"
        return state, newly_requested

    def cancellation_requested(self, run_id: str) -> bool:
        return (self.runs_dir / f"{run_id}.cancel").is_file()

    def mark_cancellation_applied(self, run_id: str) -> None:
        return


class SqliteRunStore:
    """Persist run state and queryable run events in SQLite."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        ensure_current_state_layout(self.state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "runs.sqlite3"
        self._initialize()

    def save(self, state: RunState) -> None:
        with self._connection() as connection:
            connection.execute("begin immediate")
            cancellation = connection.execute(
                "select status from run_cancellations where run_id = ?",
                (state["run_id"],),
            ).fetchone()
            if cancellation and str(state.get("status", "")) != "cancelled":
                cancelled = _cancel_state(state)
                state.clear()
                state.update(cancelled)
            _upsert_sqlite_state(connection, state)
            if cancellation and str(cancellation[0]) == "requested":
                connection.execute(
                    "update run_cancellations set status = 'applied', applied_at = ? where run_id = ?",
                    (_utc_now(), state["run_id"]),
                )

    def start_execution(
        self, state: RunState, owner_id: str, execution_id: str
    ) -> None:
        owner = _required_execution_value(owner_id, "owner")
        execution = _required_execution_value(execution_id, "id")
        with self._connection() as connection:
            connection.execute("begin immediate")
            existing = connection.execute(
                "select 1 from runs where run_id = ?", (state["run_id"],)
            ).fetchone()
            if existing:
                raise ExecutionFencedError("execution ownership was fenced")
            _upsert_sqlite_state(connection, state)
            now = _utc_now()
            connection.execute(
                """
                insert into run_executions (
                    run_id, owner_id, execution_id, status, claimed_at, updated_at
                ) values (?, ?, ?, 'active', ?, ?)
                """,
                (state["run_id"], owner, execution, now, now),
            )

    def claim_execution(
        self, run_id: str, owner_id: str, execution_id: str
    ) -> None:
        owner = _required_execution_value(owner_id, "owner")
        execution = _required_execution_value(execution_id, "id")
        with self._connection() as connection:
            connection.execute("begin immediate")
            run = connection.execute(
                "select status from runs where run_id = ?", (run_id,)
            ).fetchone()
            if run is None:
                raise FileNotFoundError(f"run not found: {run_id}")
            if str(run[0]) != "waiting":
                raise ExecutionFencedError("execution ownership was fenced")
            ticket = connection.execute(
                "select status from run_executions where run_id = ?", (run_id,)
            ).fetchone()
            if ticket and str(ticket[0]) != "released":
                raise ExecutionFencedError("execution ownership was fenced")
            now = _utc_now()
            connection.execute(
                """
                insert into run_executions (
                    run_id, owner_id, execution_id, status, claimed_at, updated_at
                ) values (?, ?, ?, 'active', ?, ?)
                on conflict(run_id) do update set
                    owner_id = excluded.owner_id,
                    execution_id = excluded.execution_id,
                    status = 'active',
                    claimed_at = excluded.claimed_at,
                    updated_at = excluded.updated_at
                """,
                (run_id, owner, execution, now, now),
            )

    def save_execution(
        self, state: RunState, owner_id: str, execution_id: str
    ) -> None:
        owner = _required_execution_value(owner_id, "owner")
        execution = _required_execution_value(execution_id, "id")
        with self._connection() as connection:
            connection.execute("begin immediate")
            ticket = connection.execute(
                """
                select status from run_executions
                where run_id = ? and owner_id = ? and execution_id = ?
                """,
                (state["run_id"], owner, execution),
            ).fetchone()
            if not ticket or str(ticket[0]) != "active":
                raise ExecutionFencedError("execution ownership was fenced")
            cancellation = connection.execute(
                "select status from run_cancellations where run_id = ?",
                (state["run_id"],),
            ).fetchone()
            if cancellation and str(state.get("status", "")) != "cancelled":
                cancelled = _cancel_state(state)
                state.clear()
                state.update(cancelled)
            _upsert_sqlite_state(connection, state)
            status = str(state.get("status", ""))
            ticket_status = "active" if status in {"created", "running"} else "released"
            connection.execute(
                """
                update run_executions set status = ?, updated_at = ?
                where run_id = ? and owner_id = ? and execution_id = ? and status = 'active'
                """,
                (ticket_status, _utc_now(), state["run_id"], owner, execution),
            )
            if cancellation and str(cancellation[0]) == "requested":
                connection.execute(
                    """
                    update run_cancellations set status = 'applied', applied_at = ?
                    where run_id = ?
                    """,
                    (_utc_now(), state["run_id"]),
                )

    def ensure_execution_active(
        self, run_id: str, owner_id: str, execution_id: str
    ) -> None:
        owner = _required_execution_value(owner_id, "owner")
        execution = _required_execution_value(execution_id, "id")
        with self._connection() as connection:
            row = connection.execute(
                """
                select 1 from run_executions
                where run_id = ? and owner_id = ? and execution_id = ?
                  and status = 'active'
                """,
                (run_id, owner, execution),
            ).fetchone()
        if row is None:
            raise ExecutionFencedError("execution ownership was fenced")

    def recover_interrupted(self, current_owner: str, max_items: int = None) -> List[RunState]:
        recovered, _processed = self.recover_interrupted_batch(
            current_owner, max_items=max_items
        )
        return recovered

    def recover_interrupted_batch(
        self, current_owner: str, max_items: int = None
    ) -> Tuple[List[RunState], int]:
        owner = _required_execution_value(current_owner, "owner")
        if max_items is not None:
            _validate_interrupted_recovery_limit(max_items)
        recovered: List[RunState] = []
        processed = 0
        with self._connection() as connection:
            connection.execute("begin immediate")
            rows = _iter_foreign_active_execution_rows(connection, owner)
            for run_id, raw_state in rows:
                processed += 1
                state = _decode_sqlite_run_state(raw_state)
                if str(state.get("status", "")) not in {"created", "running"}:
                    connection.execute(
                        "update run_executions set status = 'released', updated_at = ? where run_id = ?",
                        (_utc_now(), str(run_id)),
                    )
                    continue
                interrupted = _interrupt_state(state)
                _upsert_sqlite_state(connection, interrupted)
                connection.execute(
                    """
                    update run_executions set status = 'interrupted', updated_at = ?
                    where run_id = ? and status = 'active'
                    """,
                    (_utc_now(), str(run_id)),
                )
                connection.execute(
                    """
                    update run_cancellations set status = 'applied', applied_at = ?
                    where run_id = ? and status = 'requested'
                    """,
                    (_utc_now(), str(run_id)),
                )
                recovered.append(interrupted)
                if max_items is not None and processed >= max_items:
                    break
        return recovered, processed

    def iter_interrupted_runs(self, after_run_id: str = ""):
        """Stream interrupted run states with an optional stable cursor."""

        with self._connection() as connection:
            rows = _iter_interrupted_run_rows(connection, after_run_id=after_run_id)
            for (raw_state,) in rows:
                yield _decode_sqlite_run_state(raw_state)

    def load(self, run_id: str) -> RunState:
        with self._connection() as connection:
            row = connection.execute("select state_json from runs where run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise FileNotFoundError(f"run not found: {run_id}")
        return _decode_sqlite_run_state(row[0])

    def get_run_summary(self, run_id: str) -> RunState:
        with self._connection() as connection:
            row = connection.execute(
                """
                select run_id, workflow_id, workflow_version, status, current_node,
                       event_count, node_result_count
                from run_summaries where run_id = ?
                """,
                (str(run_id),),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"run not found: {run_id}")
        return _run_summary_from_row(row)

    def get_run_detail_projection(self, run_id: str, max_events: int) -> RunState:
        """Read the bounded redacted-detail source without loading state_json.

        The complete run document can contain trigger input, workflow DSL,
        connector output, and an arbitrarily long event history.  The detail
        endpoint only needs the compact summary projection, the node overlay
        projection, and a bounded event tail, so keep those reads separate.
        """

        _validate_audit_event_limit(max_events)
        with self._connection() as connection:
            row = connection.execute(
                """
                select run_id, workflow_id, workflow_version, status,
                       current_node, event_count, node_result_count,
                       detail_projection_json
                from run_summaries
                where run_id = ?
                """,
                (str(run_id),),
            ).fetchone()
            if row is None:
                raise FileNotFoundError(f"run not found: {run_id}")
            event_rows = connection.execute(
                """
                select payload_json
                from run_events
                where run_id = ?
                order by sequence desc
                limit ?
                """,
                (str(run_id), max_events),
            ).fetchall()

        try:
            projection = json.loads(str(row[7]))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("SQLite run detail projection is not valid JSON") from error
        if not isinstance(projection, dict):
            raise ValueError("SQLite run detail projection must be an object")
        node_ids = projection.get("node_ids", [])
        node_overlays = projection.get("node_overlays", {})
        if not isinstance(node_ids, list) or not isinstance(node_overlays, dict):
            raise ValueError("SQLite run detail projection is invalid")
        events = []
        for (payload_json,) in reversed(event_rows):
            try:
                event = json.loads(str(payload_json))
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError("SQLite run event is not valid JSON") from error
            if isinstance(event, dict):
                events.append(event)
        return {
            "run_id": str(row[0]),
            "workflow_id": str(row[1]),
            "workflow_version": str(row[2]),
            "status": str(row[3]),
            "current_node": str(row[4]),
            "event_count": max(0, int(row[5])),
            "node_result_count": max(0, int(row[6])),
            "events": events,
            "node_ids": [str(node_id) for node_id in node_ids],
            "node_overlays": node_overlays,
            "created_at": "",
            "updated_at": "",
        }

    def count(self) -> int:
        """Count persisted run rows without loading their state documents."""

        with self._connection() as connection:
            return int(connection.execute("select count(*) from runs").fetchone()[0])

    def run_event_type_counts(self, run_ids: List[str]) -> Dict[str, Dict[str, int]]:
        """Count compact event rows for selected runs without loading state JSON."""

        selected = [str(run_id) for run_id in run_ids if str(run_id)]
        if not selected:
            return {}
        placeholders = ",".join("?" for _ in selected)
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                select run_id, event_type, count(*)
                from run_events
                where run_id in ({placeholders})
                group by run_id, event_type
                order by run_id, event_type
                """,
                selected,
            ).fetchall()
        counts = {}
        for run_id, event_type, count in rows:
            counts.setdefault(str(run_id), {})[str(event_type)] = int(count)
        return counts

    def list(self) -> List[RunState]:
        with self._connection() as connection:
            rows = connection.execute("select state_json from runs order by run_id").fetchall()
        return [_decode_sqlite_run_state(row[0]) for row in rows]

    def list_bounded(self, limit: int) -> List[RunState]:
        """Read only the newest bounded run states without loading the full table."""

        _validate_run_list_limit(limit)
        with self._connection() as connection:
            rows = connection.execute(
                """
                select run_summaries.run_id, run_summaries.workflow_id,
                       run_summaries.workflow_version, run_summaries.status,
                       run_summaries.current_node, run_summaries.event_count,
                       run_summaries.node_result_count
                from run_summaries
                join runs using (run_id)
                order by runs.updated_at desc, run_summaries.run_id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [_run_summary_from_row(row) for row in reversed(rows)]

    def snapshot_window(self, limit: int) -> Dict[str, object]:
        """Read recent run state plus aggregate counts without loading all rows."""

        _validate_snapshot_limit(limit)
        with self._connection() as connection:
            total = int(connection.execute("select count(*) from runs").fetchone()[0])
            status_rows = connection.execute(
                "select status, count(*) from run_summaries group by status order by status"
            ).fetchall()
            rows = connection.execute(
                """
                select run_summaries.run_id, run_summaries.workflow_id,
                       run_summaries.workflow_version, run_summaries.status,
                       run_summaries.current_node, run_summaries.event_count,
                       run_summaries.node_result_count
                from run_summaries
                join runs using (run_id)
                order by runs.updated_at desc, run_summaries.run_id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return {
            "total": total,
            "status_counts": {
                str(status): int(count) for status, count in status_rows
            },
            "items": [_run_summary_from_row(row) for row in reversed(rows)],
        }

    def run_page(
        self,
        limit: int,
        *,
        before_updated_at: str = "",
        before_run_id: str = "",
        status: str = "",
        workflow_id: str = "",
    ) -> Dict[str, object]:
        """Return a bounded, filtered cursor page without loading all runs."""

        _validate_page_limit(limit)
        before_updated_at = str(before_updated_at or "")
        before_run_id = str(before_run_id or "")
        if bool(before_updated_at) != bool(before_run_id):
            raise ValueError("run page cursor must contain updated_at and run_id")
        filter_clauses = []
        filter_values = []
        if status:
            filter_clauses.append("run_summaries.status = ?")
            filter_values.append(str(status))
        if workflow_id:
            filter_clauses.append("run_summaries.workflow_id = ?")
            filter_values.append(str(workflow_id))
        clauses = list(filter_clauses)
        values = list(filter_values)
        if before_updated_at:
            clauses.append(
                "(runs.updated_at < ? or "
                "(runs.updated_at = ? and run_summaries.run_id < ?))"
            )
            values.extend([before_updated_at, before_updated_at, before_run_id])
        filter_where = (
            " where " + " and ".join(filter_clauses) if filter_clauses else ""
        )
        where = " where " + " and ".join(clauses) if clauses else ""
        with self._connection() as connection:
            total = int(
                connection.execute(
                    f"select count(*) from run_summaries{filter_where}", filter_values
                ).fetchone()[0]
            )
            status_rows = connection.execute(
                f"select status, count(*) from run_summaries{filter_where} group by status order by status",
                filter_values,
            ).fetchall()
            rows = connection.execute(
                f"""
                select run_summaries.run_id, runs.updated_at,
                       run_summaries.workflow_id, run_summaries.workflow_version,
                       run_summaries.status, run_summaries.current_node,
                       run_summaries.event_count, run_summaries.node_result_count
                from run_summaries join runs using (run_id){where}
                order by runs.updated_at desc, run_summaries.run_id desc
                limit ?
                """,
                values + [limit + 1],
            ).fetchall()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            next_cursor = {
                "updated_at": str(page_rows[-1][1]),
                "run_id": str(page_rows[-1][0]),
            }
        return {
            "total": total,
            "status_counts": {str(status): int(count) for status, count in status_rows},
            "items": [_run_summary_from_page_row(row) for row in reversed(page_rows)],
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    def expire_waiting_workflow_deadlines(
        self, now: str, limit: int = 256
    ) -> List[RunState]:
        """Atomically expire a bounded set of waiting workflow deadlines."""

        _validate_sweep_limit(limit)
        expired = []
        with self._connection() as connection:
            connection.execute("begin immediate")
            rows = connection.execute(
                """
                select run_id, state_json
                from runs
                where status = 'waiting'
                  and state_json like '%"workflow_deadline_at": "%'
                  and state_json not like '%"workflow_deadline_at": ""%'
                order by updated_at, run_id
                limit ?
                """,
                (limit,),
            ).fetchall()
            for run_id, raw_state in rows:
                cancellation = connection.execute(
                    "select status from run_cancellations where run_id = ?",
                    (str(run_id),),
                ).fetchone()
                if cancellation and str(cancellation[0]) == "requested":
                    continue
                state = _decode_sqlite_run_state(raw_state)
                updated = _expire_waiting_workflow_state(state, now)
                if updated is None:
                    continue
                _save_sqlite_state(connection, updated)
                expired.append(updated)
        return expired

    def list_workflow_timeout_runs(self, limit: int = 256) -> List[RunState]:
        """Return a bounded set of terminal workflow-timeout states."""

        _validate_sweep_limit(limit)
        with self._connection() as connection:
            rows = connection.execute(
                """
                select state_json
                from runs
                where status = 'failed'
                  and state_json like '%"error_code": "workflow_timeout"%'
                order by updated_at, run_id
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [
            state
            for (raw_state,) in rows
            if (state := _decode_sqlite_run_state(raw_state)).get("error_code")
            == "workflow_timeout"
        ]

    def request_cancellation(self, run_id: str):
        with self._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select state_json from runs where run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise FileNotFoundError(f"run not found: {run_id}")
            state = _decode_sqlite_run_state(row[0])
            status = str(state.get("status", ""))
            existing = connection.execute(
                "select status from run_cancellations where run_id = ?", (run_id,)
            ).fetchone()
            if status == "cancelled":
                if existing and str(existing[0]) != "applied":
                    connection.execute(
                        "update run_cancellations set status = 'applied', applied_at = ? where run_id = ?",
                        (_utc_now(), run_id),
                    )
                return state, False
            if status in {"completed", "failed", "interrupted"}:
                raise ValueError(f"run {run_id} is already {status}")
            newly_requested = existing is None
            if newly_requested:
                connection.execute(
                    """
                    insert into run_cancellations (run_id, requested_at, status, applied_at)
                    values (?, ?, 'requested', '')
                    """,
                    (run_id, _utc_now()),
                )
            if status == "waiting":
                state = _cancel_state(state)
                _save_sqlite_state(connection, state)
                connection.execute(
                    "update run_cancellations set status = 'applied', applied_at = ? where run_id = ?",
                    (_utc_now(), run_id),
                )
            else:
                state = dict(state)
                state["status"] = "cancel_requested"
            return state, newly_requested

    def cancellation_requested(self, run_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "select status from run_cancellations where run_id = ?", (run_id,)
            ).fetchone()
        return bool(row and str(row[0]) == "requested")

    def mark_cancellation_applied(self, run_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                update run_cancellations
                set status = 'applied', applied_at = ?
                where run_id = ? and status = 'requested'
                """,
                (_utc_now(), run_id),
            )

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
                create table if not exists run_cancellations (
                    run_id text primary key,
                    requested_at text not null,
                    status text not null check(status in ('requested', 'applied')),
                    applied_at text not null,
                    foreign key (run_id) references runs(run_id) on delete cascade
                )
                """
            )
            connection.execute(
                """
                create table if not exists run_executions (
                    run_id text primary key,
                    owner_id text not null,
                    execution_id text not null,
                    status text not null check(status in ('active', 'released', 'interrupted')),
                    claimed_at text not null,
                    updated_at text not null,
                    foreign key (run_id) references runs(run_id) on delete cascade
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
            connection.execute(
                """
                create table if not exists run_summaries (
                    run_id text primary key,
                    workflow_id text not null,
                    workflow_version text not null,
                    status text not null,
                    current_node text not null,
                    event_count integer not null,
                    node_result_count integer not null,
                    updated_at text not null,
                    detail_projection_json text not null default '',
                    foreign key (run_id) references runs(run_id) on delete cascade
                )
                """
            )
            summary_columns = {
                str(row[1])
                for row in connection.execute(
                    'pragma table_info("run_summaries")'
                ).fetchall()
            }
            if "detail_projection_json" not in summary_columns:
                connection.execute(
                    "alter table run_summaries add column detail_projection_json text not null default ''"
                )
            connection.execute(
                "delete from run_summaries where run_id not in (select run_id from runs)"
            )
            summary_count = int(
                connection.execute("select count(*) from run_summaries").fetchone()[0]
            )
            run_count = int(connection.execute("select count(*) from runs").fetchone()[0])
            if summary_count < run_count:
                rows = connection.execute(
                    """
                    select runs.run_id, runs.state_json
                    from runs left join run_summaries
                      on run_summaries.run_id = runs.run_id
                    where run_summaries.run_id is null
                    order by runs.run_id
                    """
                )
                for run_id, raw_state in rows:
                    state = _decode_sqlite_run_state(raw_state)
                    _upsert_sqlite_summary(connection, state)
            projection_rows = connection.execute(
                """
                select runs.run_id, runs.state_json
                from runs join run_summaries using (run_id)
                where run_summaries.detail_projection_json = ''
                order by runs.run_id
                """
            )
            for run_id, raw_state in projection_rows:
                state = _decode_sqlite_run_state(raw_state)
                _upsert_sqlite_summary(connection, state)

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
        try:
            index = _read_json_control_index(self.index_path)
        except FileNotFoundError:
            return {}
        if not isinstance(index, dict):
            raise ValueError("workflow index must be an object")
        return index

    def get_workflow_record(self, workflow_id: str, version: str) -> WorkflowRecord:
        index = self.load_index()
        key = _workflow_record_key(workflow_id, version)
        if key not in index:
            raise ValueError(f"workflow version not found: {workflow_id}@{version}")
        return index[key]

    def save_index(self, index: Dict[str, WorkflowRecord]) -> None:
        self.index_path.write_bytes(_encode_json_control_index(index))

    def count_workflow_records(self) -> int:
        """Count JSON registry records while preserving the complete-list API."""

        return len(self.load_index())

    def snapshot_window(self, limit: int) -> Dict[str, object]:
        """Read a bounded JSON control window with aggregate totals."""

        _validate_snapshot_limit(limit)
        index = self.load_index()
        records = sorted(
            index.values(),
            key=lambda record: (str(record.get("workflow_id", "")), str(record.get("version", ""))),
        )
        status_counts = Counter(str(record.get("status", "other")) for record in records)
        audit_events = self.list_audit_events(limit=limit)
        audit_total = 0
        if self.audit_path.exists():
            with self.audit_path.open("r", encoding="utf-8") as handle:
                audit_total = sum(
                    1 for line in _iter_bounded_audit_lines(handle) if line.strip()
                )
        return {
            "workflow_total": len(records),
            "workflow_status_counts": dict(status_counts),
            "workflows": records[-limit:],
            "audit_total": audit_total,
            "audit_events": audit_events,
        }

    def append_audit(self, event: AuditEvent) -> None:
        self.append_audit_batch([event])

    def append_audit_batch(self, events: List[AuditEvent]) -> None:
        """Append one logical audit emission as a single file write."""

        if not isinstance(events, list):
            raise ValueError("audit events must be a list")
        payload = "".join(
            _encode_audit_event(event) + "\n"
            for event in events
        )
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(payload)

    def append_audit_batch_if_missing(self, events: List[AuditEvent]) -> None:
        """Append only canonical payloads not already present."""

        missing = [event for event in events if not self.audit_event_exists(event)]
        if missing:
            self.append_audit_batch(missing)

    def list_audit_events(
        self,
        workflow_id: str = "",
        version: str = "",
        run_id: str = "",
        event_type: str = "",
        limit: int = None,
    ) -> List[AuditEvent]:
        """Return audit events, optionally retaining only the newest matches."""

        _validate_audit_event_limit(limit)
        if not self.audit_path.exists():
            return []
        events = deque(maxlen=limit) if limit is not None else []
        with self.audit_path.open("r", encoding="utf-8") as handle:
            lines = _iter_bounded_audit_lines(handle)
            for line in lines:
                if not line.strip():
                    continue
                event = _decode_audit_event(line)
                if not _audit_event_matches(
                    event,
                    workflow_id=workflow_id,
                    version=version,
                    run_id=run_id,
                    event_type=event_type,
                ):
                    continue
                events.append(event)
        return list(events)

    def audit_event_exists(self, event: AuditEvent) -> bool:
        """Return whether one canonical audit payload is already persisted."""

        expected = _encode_audit_event(event)
        if not self.audit_path.exists():
            return False
        with self.audit_path.open("r", encoding="utf-8") as handle:
            for line in _iter_bounded_audit_lines(handle):
                if not line.strip():
                    continue
                try:
                    candidate = _decode_audit_event(line)
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if json.dumps(candidate, ensure_ascii=False, sort_keys=True) == expected:
                    return True
        return False

    def audit_event_type_exists_for_run(self, run_id: str, event_type: str) -> bool:
        """Check one run/event projection without retaining audit history."""

        if not self.audit_path.exists():
            return False
        with self.audit_path.open("r", encoding="utf-8") as handle:
            for line in _iter_bounded_audit_lines(handle):
                if not line.strip():
                    continue
                try:
                    candidate = _decode_audit_event(line)
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if _audit_event_matches(
                    candidate,
                    run_id=str(run_id),
                    event_type=str(event_type),
                ):
                    return True
        return False

    def audit_event_type_counts(self, run_ids: List[str]) -> Dict[str, Dict[str, int]]:
        """Count audit event types for selected runs without retaining payloads."""

        selected = {str(run_id) for run_id in run_ids if str(run_id)}
        counts = {}
        if not selected or not self.audit_path.exists():
            return counts
        with self.audit_path.open("r", encoding="utf-8") as handle:
            for line in _iter_bounded_audit_lines(handle):
                if not line.strip():
                    continue
                event = _decode_audit_event(line)
                if not isinstance(event, dict):
                    raise ValueError("audit event must be an object")
                run_id = str(event.get("run_id", ""))
                if run_id not in selected:
                    continue
                run_counts = counts.setdefault(run_id, Counter())
                run_counts[str(event.get("type", "event"))] += 1
        return {run_id: dict(counter) for run_id, counter in counts.items()}

    def verify_audit_integrity(self) -> Dict[str, object]:
        """Report that JSON audit storage has no durable chain contract."""

        return {
            "schema_version": AUDIT_INTEGRITY_SCHEMA_VERSION,
            "status": "legacy_unsealed",
            "algorithm": "",
            "event_count": len(self.list_audit_events()),
            "head_digest": "",
            "first_invalid_sequence": 0,
            "reason": "sqlite_storage_required",
        }


class SqliteControlStore:
    """Persist workflow registry and audit metadata in SQLite."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        ensure_current_state_layout(self.state_dir)
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
        return {str(row[0]): _decode_sqlite_workflow_record(row[1]) for row in rows}

    def get_workflow_record(self, workflow_id: str, version: str) -> WorkflowRecord:
        key = _workflow_record_key(workflow_id, version)
        with self._connection() as connection:
            row = connection.execute(
                "select record_json from workflow_versions where record_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            raise ValueError(f"workflow version not found: {workflow_id}@{version}")
        return _decode_sqlite_workflow_record(row[0])

    def resolve_workflow_version(self, workflow_id: str, requested: str) -> str:
        """Resolve one SQLite workflow alias without loading the global registry."""

        workflow_id = str(workflow_id)
        requested = str(requested)
        with self._connection() as connection:
            exact = connection.execute(
                "select 1 from workflow_versions where record_key = ? limit 1",
                (_workflow_record_key(workflow_id, requested),),
            ).fetchone()
            if exact is not None:
                return requested
            matches = []
            rows = _iter_workflow_records_for_id(connection, workflow_id)
            for _record_key, raw_record in rows:
                record = _decode_sqlite_workflow_record(raw_record)
                if (
                    record.get("status") == "published"
                    and requested in _sqlite_record_aliases(record)
                ):
                    matches.append(str(record.get("version", "")))
        matches = sorted(version for version in matches if version)
        if len(matches) > 1:
            raise ValueError(f"workflow alias is ambiguous: {workflow_id}@{requested}")
        return matches[0] if matches else requested

    def count_workflow_records(self) -> int:
        """Count published registry rows without loading their JSON records."""

        with self._connection() as connection:
            return int(
                connection.execute("select count(*) from workflow_versions").fetchone()[0]
            )

    def iter_workflow_records(self):
        """Stream published registry records in stable key order."""

        with self._connection() as connection:
            rows = connection.execute(
                "select record_key, record_json from workflow_versions order by record_key"
            )
            for record_key, record_json in rows:
                yield str(record_key), _decode_sqlite_workflow_record(record_json)

    def count_referenced_artifacts(self) -> int:
        """Count distinct safe-looking artifact references in SQLite."""

        with self._connection() as connection:
            row = connection.execute(
                """
                select count(distinct artifact)
                from workflow_versions
                where artifact like 'workflows/%'
                  and artifact like '%.json'
                  and artifact <> 'workflows/index.json'
                  and artifact not like '%\\%'
                  and artifact not like '%//%'
                  and artifact not like '%/./%'
                  and artifact not like '%/../%'
                """
            ).fetchone()
        return int(row[0])

    def artifact_reference_exists(self, relative: str) -> bool:
        """Check one normalized artifact reference without loading the registry."""

        with self._connection() as connection:
            row = connection.execute(
                "select 1 from workflow_versions where artifact = ? limit 1",
                (str(relative),),
            ).fetchone()
        return row is not None

    def audit_event_type_exists_for_run(self, run_id: str, event_type: str) -> bool:
        """Check one run/event projection without loading audit payloads."""

        with self._connection() as connection:
            row = connection.execute(
                "select 1 from audit_events where run_id = ? and event_type = ? limit 1",
                (str(run_id), str(event_type)),
            ).fetchone()
        return row is not None

    def save_index(self, index: Dict[str, WorkflowRecord]) -> None:
        serialized_records = [
            (
                key,
                record,
                _encode_sqlite_workflow_record(record),
            )
            for key, record in index.items()
        ]
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
                        serialized,
                    )
                    for key, record, serialized in serialized_records
                ],
            )

    def publish_workflow_record(
        self,
        record: WorkflowRecord,
        *,
        artifact_path: Path = None,
        audit_event: AuditEvent,
    ) -> WorkflowRecord:
        """Insert one immutable registry record and its audit row atomically."""

        workflow_id = str(record.get("workflow_id", ""))
        version = str(record.get("version", ""))
        key = _workflow_record_key(workflow_id, version)
        serialized_record = _encode_sqlite_workflow_record(record)
        with self._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select record_json from workflow_versions where record_key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                try:
                    existing = _decode_sqlite_workflow_record(row[0])
                except (TypeError, ValueError, json.JSONDecodeError) as error:
                    raise ValueError("workflow registry record is invalid") from error
                if str(existing.get("checksum", "")) != str(record.get("checksum", "")):
                    raise ValueError(
                        f"published workflow version is immutable: {workflow_id}@{version}"
                    )
                return existing

            if artifact_path is not None:
                _require_publish_artifact(
                    artifact_path,
                    str(record.get("checksum", "")),
                    root=self.state_dir,
                )

            connection.execute(
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
                (
                    key,
                    workflow_id,
                    str(record.get("name", "")),
                    version,
                    str(record.get("status", "")),
                    str(record.get("checksum", "")),
                    str(record.get("artifact", "")),
                    str(record.get("published_at", "")),
                    str(record.get("deprecated_at", "")),
                    serialized_record,
                ),
            )
            _append_audit_connection(connection, audit_event)
            return dict(record)

    def cleanup_unregistered_artifact(
        self,
        record_key: str,
        artifact_path: Path,
        checksum: str,
    ) -> bool:
        """Remove a newly-created artifact only while its registry key is absent."""

        with self._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select 1 from workflow_versions where record_key = ?",
                (str(record_key),),
            ).fetchone()
            if row is not None:
                return False
            if not _publish_artifact_matches(
                artifact_path, checksum, root=self.state_dir
            ):
                return False
            try:
                artifact_path.unlink()
            except FileNotFoundError:
                return False
            return True

    def deprecate_workflow_record(
        self,
        workflow_id: str,
        version: str,
        *,
        deprecated_at: str,
        audit_event: AuditEvent,
    ) -> WorkflowRecord:
        """Deprecate one registry record and its audit row atomically."""

        key = _workflow_record_key(workflow_id, version)
        with self._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select record_json from workflow_versions where record_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                raise ValueError(f"workflow version not found: {workflow_id}@{version}")
            try:
                current = _decode_sqlite_workflow_record(row[0])
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError("workflow registry record is invalid") from error
            record = dict(current)
            was_deprecated = record.get("status") == "deprecated"
            aliases = _sqlite_record_aliases(record)
            changed = bool(aliases) or not was_deprecated
            if aliases:
                record.pop("aliases", None)
            if not was_deprecated:
                record["status"] = "deprecated"
                record["deprecated_at"] = str(deprecated_at)
            if not changed:
                return record

            connection.execute(
                "update workflow_versions set status = ?, deprecated_at = ?, record_json = ? where record_key = ?",
                (
                    str(record.get("status", "deprecated")),
                    str(record.get("deprecated_at", "")),
                    _encode_sqlite_workflow_record(record),
                    key,
                ),
            )
            if not was_deprecated:
                _append_audit_connection(connection, audit_event)
            return record

    def promote_workflow_alias(
        self,
        workflow_id: str,
        version: str,
        alias: str,
        *,
        expected_current_version: str = "",
        audit_event: AuditEvent,
    ) -> WorkflowRecord:
        """Atomically move one alias and append its audit event in SQLite."""

        with self._connection() as connection:
            connection.execute("begin immediate")
            target_key = _workflow_record_key(workflow_id, version)
            target_row = connection.execute(
                "select record_json from workflow_versions where record_key = ?",
                (target_key,),
            ).fetchone()
            if target_row is None:
                raise ValueError(f"workflow version not found: {workflow_id}@{version}")
            target = dict(_decode_sqlite_workflow_record(target_row[0]))
            if target.get("status") != "published":
                raise ValueError(
                    f"workflow version is not published: {workflow_id}@{version}"
                )

            current_versions = []
            changed_records = []
            rows = _iter_workflow_records_for_id(connection, workflow_id)
            for record_key, raw_record in rows:
                existing = _decode_sqlite_workflow_record(raw_record)
                existing_aliases = _sqlite_record_aliases(existing)
                if alias not in existing_aliases:
                    continue
                if existing.get("status") == "published":
                    current_versions.append(str(existing.get("version", "")))
                updated = dict(existing)
                existing_aliases.remove(alias)
                if existing_aliases:
                    updated["aliases"] = existing_aliases
                else:
                    updated.pop("aliases", None)
                changed_records.append((str(record_key), updated))
            current_versions.sort()
            if expected_current_version and current_versions != [
                str(expected_current_version)
            ]:
                raise ValueError(
                    f"workflow alias precondition failed: {workflow_id}@{alias}"
                )
            if current_versions == [version] and alias in _sqlite_record_aliases(target):
                return target

            changed_keys = {key for key, _updated in changed_records}
            updated_by_key = {key: updated for key, updated in changed_records}
            target = dict(updated_by_key.get(target_key, target))
            target_aliases = _sqlite_record_aliases(target)
            if alias not in target_aliases:
                target_aliases.append(alias)
                target["aliases"] = sorted(set(target_aliases))
                updated_by_key[target_key] = target
                changed_keys.add(target_key)

            if changed_keys:
                serialized_updates = [
                    (_encode_sqlite_workflow_record(updated_by_key[key]), key)
                    for key in sorted(changed_keys)
                ]
                connection.executemany(
                    "update workflow_versions set record_json = ? where record_key = ?",
                    serialized_updates,
                )
                _append_audit_connection(connection, audit_event)
            return target

    def append_audit(self, event: AuditEvent) -> None:
        self.append_audit_batch([event])

    def append_audit_batch(self, events: List[AuditEvent]) -> None:
        """Append one logical audit emission in one SQLite transaction."""

        if not isinstance(events, list):
            raise ValueError("audit events must be a list")
        with self._connection() as connection:
            connection.execute("begin immediate")
            for event in events:
                _append_audit_connection(connection, event)

    def append_audit_batch_if_missing(self, events: List[AuditEvent]) -> None:
        """Atomically append only canonical payloads not already present."""

        if not isinstance(events, list):
            raise ValueError("audit events must be a list")
        with self._connection() as connection:
            connection.execute("begin immediate")
            for event in events:
                payload_json = _encode_audit_event(event)
                exists = connection.execute(
                    "select 1 from audit_events where payload_json = ? limit 1",
                    (payload_json,),
                ).fetchone()
                if exists is None:
                    _append_audit_connection(connection, event)

    def verify_audit_integrity(self) -> Dict[str, object]:
        with self._connection() as connection:
            return _verify_audit_integrity_connection(connection)

    def claim_trigger_idempotency(
        self,
        workflow_id: str,
        workflow_version: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> Dict[str, object]:
        """Atomically reserve one trigger key before executing its side effects."""

        now = _utc_now()
        with self._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                """
                select request_fingerprint, status, response_json
                from trigger_idempotency
                where workflow_id = ? and workflow_version = ? and idempotency_key = ?
                """,
                (workflow_id, workflow_version, idempotency_key),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    insert into trigger_idempotency (
                        workflow_id, workflow_version, idempotency_key,
                        request_fingerprint, status, response_json, created_at, updated_at
                    ) values (?, ?, ?, ?, 'pending', '', ?, ?)
                    """,
                    (
                        workflow_id,
                        workflow_version,
                        idempotency_key,
                        request_fingerprint,
                        now,
                        now,
                    ),
                )
                return {
                    "status": "claimed",
                    "request_fingerprint": request_fingerprint,
                    "response_json": "",
                }
            response_json = str(row[2])
            if response_json:
                _decode_sqlite_trigger_response(response_json)
            elif str(row[1]) == "completed":
                raise ValueError("SQLite trigger response is empty")
            return {
                "status": str(row[1]),
                "request_fingerprint": str(row[0]),
                "response_json": response_json,
            }

    def complete_trigger_idempotency(
        self,
        workflow_id: str,
        workflow_version: str,
        idempotency_key: str,
        request_fingerprint: str,
        response: Dict[str, object],
    ) -> None:
        """Persist only the compact trigger response after execution completes."""

        response_json = _encode_sqlite_trigger_response(response)
        with self._connection() as connection:
            updated = connection.execute(
                """
                update trigger_idempotency
                set status = 'completed', response_json = ?, updated_at = ?
                where workflow_id = ? and workflow_version = ? and idempotency_key = ?
                  and request_fingerprint = ? and status = 'pending'
                """,
                (
                    response_json,
                    _utc_now(),
                    workflow_id,
                    workflow_version,
                    idempotency_key,
                    request_fingerprint,
                ),
            ).rowcount
            if updated != 1:
                raise ValueError("trigger idempotency claim is no longer pending")

    def mark_trigger_idempotency_unresolved(
        self,
        workflow_id: str,
        workflow_version: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> None:
        """Fail closed when execution outcome is not known to be safe to replay."""

        with self._connection() as connection:
            connection.execute(
                """
                update trigger_idempotency
                set status = 'unresolved', updated_at = ?
                where workflow_id = ? and workflow_version = ? and idempotency_key = ?
                  and request_fingerprint = ? and status = 'pending'
                """,
                (
                    _utc_now(),
                    workflow_id,
                    workflow_version,
                    idempotency_key,
                    request_fingerprint,
                ),
            )

    def list_audit_events(
        self,
        workflow_id: str = "",
        version: str = "",
        run_id: str = "",
        event_type: str = "",
        limit: int = None,
    ) -> List[AuditEvent]:
        """Return audit events, applying filters and a newest-first storage bound."""

        _validate_audit_event_limit(limit)
        clauses = []
        parameters = []
        for column, value in (
            ("workflow_id", workflow_id),
            ("workflow_version", version),
            ("run_id", run_id),
            ("event_type", event_type),
        ):
            if value:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        query = "select payload_json from audit_events"
        if clauses:
            query += " where " + " and ".join(clauses)
        query += " order by sequence"
        if limit is not None:
            query += " desc limit ?"
            parameters.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        events = [_decode_audit_event(row[0]) for row in rows]
        if limit is not None:
            events.reverse()
        return events

    def audit_page(
        self,
        max_items: int,
        *,
        before_sequence: int = 0,
        workflow_id: str = "",
        version: str = "",
        run_id: str = "",
        event_type: str = "",
    ) -> Dict[str, object]:
        """Read one cursor-bounded audit page without retaining the history."""

        _validate_audit_event_limit(max_items)
        if (
            isinstance(before_sequence, bool)
            or not isinstance(before_sequence, int)
            or before_sequence < 0
        ):
            raise ValueError("audit page cursor must be a non-negative integer")
        clauses = []
        parameters = []
        for column, value in (
            ("workflow_id", workflow_id),
            ("workflow_version", version),
            ("run_id", run_id),
            ("event_type", event_type),
        ):
            if value:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        where = " where " + " and ".join(clauses) if clauses else ""
        cursor_clause = ""
        if before_sequence:
            cursor_clause = (" and " if where else " where ") + "sequence < ?"
            parameters.append(before_sequence)
        with self._connection() as connection:
            total_parameters = list(parameters[:-1]) if before_sequence else list(parameters)
            total = int(
                connection.execute(
                    "select count(*) from audit_events" + where,
                    total_parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                "select sequence, payload_json from audit_events"
                + where
                + cursor_clause
                + " order by sequence desc limit ?",
                parameters + [max_items + 1],
            ).fetchall()
        has_more = len(rows) > max_items
        selected = rows[:max_items]
        events = []
        for sequence, payload_json in reversed(selected):
            events.append(
                {"sequence": int(sequence), "event": _decode_audit_event(payload_json)}
            )
        next_cursor = int(selected[-1][0]) if has_more and selected else 0
        return {
            "total": total,
            "items": events,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    def audit_event_exists(self, event: AuditEvent) -> bool:
        """Return whether one canonical audit payload is already persisted."""

        payload_json = _encode_audit_event(event)
        with self._connection() as connection:
            row = connection.execute(
                "select 1 from audit_events where payload_json = ? limit 1",
                (payload_json,),
            ).fetchone()
        return row is not None

    def audit_event_type_counts(self, run_ids: List[str]) -> Dict[str, Dict[str, int]]:
        """Count audit event types for selected runs without loading payloads."""

        selected = [str(run_id) for run_id in run_ids if str(run_id)]
        if not selected:
            return {}
        placeholders = ",".join("?" for _ in selected)
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                select run_id, event_type, count(*)
                from audit_events
                where run_id in ({placeholders})
                group by run_id, event_type
                order by run_id, event_type
                """,
                selected,
            ).fetchall()
        counts = {}
        for run_id, event_type, count in rows:
            counts.setdefault(str(run_id), {})[str(event_type)] = int(count)
        return counts

    def snapshot_window(self, limit: int) -> Dict[str, object]:
        """Read recent registry and audit rows plus totals in one SQLite view."""

        with self._connection() as connection:
            workflow_total = int(
                connection.execute("select count(*) from workflow_versions").fetchone()[0]
            )
            workflow_status_rows = connection.execute(
                """
                select status, count(*) from workflow_versions
                group by status order by status
                """
            ).fetchall()
            workflow_rows = connection.execute(
                """
                select record_json from workflow_versions
                order by published_at desc, record_key desc
                limit ?
                """,
                (limit,),
            ).fetchall()
            audit_total = int(
                connection.execute("select count(*) from audit_events").fetchone()[0]
            )
            audit_rows = connection.execute(
                """
                select payload_json from audit_events
                order by sequence desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return {
            "workflow_total": workflow_total,
            "workflow_status_counts": {
                str(status): int(count) for status, count in workflow_status_rows
            },
            "workflows": [
                _decode_sqlite_workflow_record(row[0]) for row in reversed(workflow_rows)
            ],
            "audit_total": audit_total,
            "audit_events": [
                _decode_audit_event(row[0]) for row in reversed(audit_rows)
            ],
        }

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
                    payload_json text not null,
                    prev_digest text not null default '',
                    digest text not null default ''
                )
                """
            )
            connection.execute(
                """
                create table if not exists trigger_idempotency (
                    workflow_id text not null,
                    workflow_version text not null,
                    idempotency_key text not null,
                    request_fingerprint text not null,
                    status text not null,
                    response_json text not null,
                    created_at text not null,
                    updated_at text not null,
                    primary key (workflow_id, workflow_version, idempotency_key)
                )
                """
            )
            _ensure_audit_integrity_schema(connection)
            connection.execute(
                "create index if not exists audit_events_run_sequence_idx "
                "on audit_events(run_id, sequence)"
            )
            connection.execute(
                "create index if not exists audit_events_type_sequence_idx "
                "on audit_events(event_type, sequence)"
            )

    def _import_json_state(self) -> None:
        if self.index_path.exists() and not self.load_index():
            index = _read_json_control_index(self.index_path)
            if isinstance(index, dict):
                self.save_index(index)

        if self.audit_path.exists() and not self.list_audit_events():
            with self.audit_path.open("r", encoding="utf-8") as handle:
                for line in _iter_bounded_audit_lines(handle):
                    if line.strip():
                        event = _decode_audit_event(line)
                        self.append_audit(event)

    def _connection(self):
        return _sqlite_connection(self.db_path)


def create_control_store(state_dir: Path, storage: str):
    if storage == "json":
        return JsonControlStore(state_dir)
    if storage == "sqlite":
        return SqliteControlStore(state_dir)
    raise ValueError(f"unsupported control storage: {storage}")


def rebuild_audit_integrity(database: Path) -> Dict[str, object]:
    """Recompute the SQLite audit chain after an intentional row cutover."""

    with closing(sqlite3.connect(Path(database))) as connection:
        connection.execute("begin immediate")
        _rebuild_audit_integrity_connection(connection)
        connection.commit()
        return _verify_audit_integrity_connection(connection)


def verify_audit_integrity(database: Path) -> Dict[str, object]:
    """Verify one SQLite audit database without returning event payloads."""

    with closing(sqlite3.connect(f"file:{Path(database)}?mode=ro", uri=True)) as connection:
        return _verify_audit_integrity_connection(connection)


@contextmanager
def _sqlite_connection(db_path: Path):
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            yield connection


def _event_value(event: Dict[str, object], key: str, default: str) -> str:
    value = event.get(key, default)
    return str(value) if value is not None else default


def _workflow_record_key(workflow_id: str, version: str) -> str:
    return f"{workflow_id}@{version}"


def _require_publish_artifact(path: Path, checksum: str, *, root: Path) -> None:
    if not _publish_artifact_matches(path, checksum, root=root):
        raise ValueError("published workflow artifact unavailable")


def _publish_artifact_matches(path: Path, checksum: str, *, root: Path) -> bool:
    value = Path(path)
    if _path_has_symlink_component(Path(root), value):
        return False
    try:
        details = value.lstat()
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
            return False
        payload = read_workflow_artifact(value)
    except (OSError, UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError):
        return False
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return bool(checksum) and hashlib.sha256(canonical.encode("utf-8")).hexdigest() == str(checksum)


def _path_has_symlink_component(root: Path, path: Path) -> bool:
    try:
        relative = Path(path).relative_to(Path(root))
    except ValueError:
        return True
    current = Path(root)
    try:
        if stat.S_ISLNK(current.lstat().st_mode):
            return True
    except OSError:
        return True
    for part in relative.parts:
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                return True
        except FileNotFoundError:
            return False
        except OSError:
            return True
    return False


def _sqlite_record_aliases(record: WorkflowRecord) -> List[str]:
    aliases = record.get("aliases", [])
    if not isinstance(aliases, list):
        return []
    return [str(alias) for alias in aliases if str(alias)]


def _iter_workflow_records_for_id(connection, workflow_id: str):
    """Stream one workflow's registry records without loading other workflows."""

    return connection.execute(
        """
        select record_key, record_json
        from workflow_versions
        where workflow_id = ?
        order by record_key
        """,
        (str(workflow_id),),
    )


def _append_audit_connection(connection, event: AuditEvent) -> None:
    previous_row = connection.execute(
        "select digest from audit_events order by sequence desc limit 1"
    ).fetchone()
    previous_digest = (
        str(previous_row[0]) if previous_row and previous_row[0] is not None else ""
    )
    payload_json = _encode_audit_event(event)
    connection.execute(
        """
        insert into audit_events (
            event_type,
            workflow_id,
            workflow_version,
            run_id,
            timestamp,
            payload_json,
            prev_digest,
            digest
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _event_value(event, "type", "event"),
            _event_value(event, "workflow_id", ""),
            _event_value(event, "workflow_version", ""),
            _event_value(event, "run_id", ""),
            _event_value(event, "timestamp", ""),
            payload_json,
            previous_digest,
            "",
        ),
    )
    sequence = int(connection.execute("select last_insert_rowid()").fetchone()[0])
    digest = _audit_digest(sequence, previous_digest, event)
    connection.execute(
        "update audit_events set digest = ? where sequence = ?",
        (digest, sequence),
    )


def _ensure_audit_integrity_schema(connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute('pragma table_info("audit_events")').fetchall()
    }
    if columns == _LEGACY_AUDIT_COLUMNS:
        connection.execute(
            "alter table audit_events add column prev_digest text not null default ''"
        )
        connection.execute(
            "alter table audit_events add column digest text not null default ''"
        )
        _rebuild_audit_integrity_connection(connection)
        return
    if columns != _CURRENT_AUDIT_COLUMNS:
        raise ValueError("SQLite table has an incompatible audit_events layout")


def _rebuild_audit_integrity_connection(connection) -> None:
    previous_digest = _AUDIT_GENESIS_DIGEST
    rows = connection.execute(
        "select sequence, payload_json from audit_events order by sequence"
    )
    for sequence, payload_json in rows:
        try:
            payload = _decode_audit_event(payload_json)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("audit event payload is invalid") from error
        if not isinstance(payload, dict):
            raise ValueError("audit event payload is invalid")
        digest = _audit_digest(int(sequence), previous_digest, payload)
        connection.execute(
            "update audit_events set prev_digest = ?, digest = ? where sequence = ?",
            (previous_digest, digest, int(sequence)),
        )
        previous_digest = digest


def _verify_audit_integrity_connection(connection) -> Dict[str, object]:
    columns = {
        str(row[1])
        for row in connection.execute('pragma table_info("audit_events")').fetchall()
    }
    if columns == _LEGACY_AUDIT_COLUMNS:
        count = int(connection.execute("select count(*) from audit_events").fetchone()[0])
        return _audit_integrity_result(
            status="legacy_unsealed",
            event_count=count,
            reason="integrity_columns_missing",
        )
    if columns != _CURRENT_AUDIT_COLUMNS:
        return _audit_integrity_result(status="invalid", reason="schema_mismatch")

    event_count = int(
        connection.execute("select count(*) from audit_events").fetchone()[0]
    )
    rows = connection.execute(
        """
        select sequence, event_type, workflow_id, workflow_version, run_id,
               timestamp, payload_json, prev_digest, digest
        from audit_events order by sequence
        """
    )
    previous_sequence = 0
    previous_digest = _AUDIT_GENESIS_DIGEST
    for (
        sequence_value,
        stored_event_type,
        stored_workflow_id,
        stored_workflow_version,
        stored_run_id,
        stored_timestamp,
        payload_json,
        stored_previous,
        stored_digest,
    ) in rows:
        try:
            sequence = int(sequence_value)
        except (TypeError, ValueError):
            return _audit_integrity_result(
                status="invalid",
                event_count=event_count,
                reason="sequence_invalid",
            )
        if sequence <= previous_sequence:
            return _audit_integrity_result(
                status="invalid",
                event_count=event_count,
                head_digest=previous_digest,
                first_invalid_sequence=sequence,
                reason="sequence_out_of_order",
            )
        try:
            payload = _decode_audit_event(payload_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return _audit_integrity_result(
                status="invalid",
                event_count=event_count,
                head_digest=previous_digest,
                first_invalid_sequence=sequence,
                reason="payload_invalid",
            )
        if not isinstance(payload, dict):
            return _audit_integrity_result(
                status="invalid",
                event_count=event_count,
                head_digest=previous_digest,
                first_invalid_sequence=sequence,
                reason="payload_invalid",
            )
        denormalized = {
            "type": (stored_event_type, "event"),
            "workflow_id": (stored_workflow_id, ""),
            "workflow_version": (stored_workflow_version, ""),
            "run_id": (stored_run_id, ""),
            "timestamp": (stored_timestamp, ""),
        }
        if any(
            key in payload and str(stored or "") != _event_value(payload, key, default)
            for key, (stored, default) in denormalized.items()
        ):
            return _audit_integrity_result(
                status="invalid",
                event_count=event_count,
                head_digest=previous_digest,
                first_invalid_sequence=sequence,
                reason="column_mismatch",
            )
        if str(stored_previous or "") != previous_digest:
            return _audit_integrity_result(
                status="invalid",
                event_count=event_count,
                head_digest=previous_digest,
                first_invalid_sequence=sequence,
                reason="prev_digest_mismatch",
            )
        expected_digest = _audit_digest(sequence, previous_digest, payload)
        if str(stored_digest or "") != expected_digest:
            return _audit_integrity_result(
                status="invalid",
                event_count=event_count,
                head_digest=previous_digest,
                first_invalid_sequence=sequence,
                reason="digest_mismatch",
            )
        previous_sequence = sequence
        previous_digest = expected_digest
    return _audit_integrity_result(
        status="valid",
        event_count=event_count,
        head_digest=previous_digest,
    )


def _audit_integrity_result(
    *,
    status: str,
    event_count: int = 0,
    head_digest: str = "",
    first_invalid_sequence: int = 0,
    reason: str = "",
) -> Dict[str, object]:
    return {
        "schema_version": AUDIT_INTEGRITY_SCHEMA_VERSION,
        "status": status,
        "algorithm": AUDIT_INTEGRITY_ALGORITHM if status != "legacy_unsealed" else "",
        "event_count": max(0, int(event_count)),
        "head_digest": head_digest if status == "valid" else "",
        "first_invalid_sequence": max(0, int(first_invalid_sequence)),
        "reason": reason,
    }


def _audit_digest(sequence: int, previous_digest: str, payload: Dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    material = (
        f"{AUDIT_INTEGRITY_ALGORITHM}\n{int(sequence)}\n"
        f"{previous_digest}\n{canonical}"
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _cancel_state(state: RunState) -> RunState:
    updated = dict(state)
    events = list(updated.get("events", []))
    node_id = str(updated.get("current_node", ""))
    if not any(
        isinstance(event, dict) and event.get("type") == "run_cancel_requested"
        for event in events
    ):
        events.append(
            {
                "type": "run_cancel_requested",
                "node_id": node_id,
                "timestamp": _utc_now(),
            }
        )
    if not any(
        isinstance(event, dict) and event.get("type") == "run_cancelled"
        for event in events
    ):
        events.append(
            {
                "type": "run_cancelled",
                "node_id": node_id,
                "timestamp": _utc_now(),
            }
        )
    updated["events"] = events
    updated["status"] = "cancelled"
    return updated


def _interrupt_state(state: RunState) -> RunState:
    updated = dict(state)
    events = list(updated.get("events", []))
    if not any(
        isinstance(event, dict) and event.get("type") == "run_interrupted"
        for event in events
    ):
        events.append(
            {
                "type": "run_interrupted",
                "node_id": str(updated.get("current_node", "")),
                "timestamp": _utc_now(),
            }
        )
    updated["events"] = events
    updated["status"] = "interrupted"
    return updated


def _iter_foreign_active_execution_rows(connection, current_owner: str):
    """Return a cursor for active executions owned by another process."""

    return connection.execute(
        """
        select e.run_id, r.state_json
        from run_executions e join runs r on r.run_id = e.run_id
        where e.status = 'active' and e.owner_id != ?
        order by e.run_id
        """,
        (str(current_owner),),
    )


def _iter_interrupted_run_rows(connection, after_run_id: str = ""):
    """Return a cursor for interrupted states in stable cursor order."""

    if after_run_id:
        return connection.execute(
            """
            select state_json
            from runs
            where status = 'interrupted' and run_id > ?
            order by run_id
            """,
            (str(after_run_id),),
        )
    return connection.execute(
        """
        select state_json
        from runs
        where status = 'interrupted'
        order by run_id
        """
    )


def _required_execution_value(value: str, field: str) -> str:
    normalized = str(value or "")
    if not normalized or len(normalized) > 128:
        raise ValueError(f"execution {field} must be a non-empty string of at most 128 characters")
    return normalized


def _validate_sweep_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 256:
        raise ValueError("workflow deadline sweep limit must be an integer from 1 through 256")


def _encode_bounded_json_document(value: object, max_bytes: int, label: str) -> bytes:
    """Serialize one local JSON document without exceeding its fixed bound."""

    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > max_bytes:
        raise ValueError(f"{label} exceeds {max_bytes} bytes")
    return raw


def _encode_sqlite_run_state(state: RunState) -> str:
    """Serialize one SQLite run state within the durable document boundary."""

    try:
        raw = json.dumps(state, ensure_ascii=False, sort_keys=True).encode("utf-8")
    except (
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
        UnicodeError,
    ) as error:
        raise ValueError("SQLite run state is not JSON serializable") from error
    if len(raw) > MAX_SQLITE_RUN_STATE_BYTES:
        raise ValueError(
            f"SQLite run state exceeds {MAX_SQLITE_RUN_STATE_BYTES} bytes"
        )
    return raw.decode("utf-8")


def _encode_sqlite_workflow_record(record: WorkflowRecord) -> str:
    """Serialize one SQLite registry record within its durable byte boundary."""

    if not isinstance(record, dict):
        raise ValueError("SQLite workflow record must be an object")
    try:
        raw = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    except (
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
        UnicodeError,
    ) as error:
        raise ValueError("SQLite workflow record is not JSON serializable") from error
    if len(raw) > MAX_SQLITE_WORKFLOW_RECORD_BYTES:
        raise ValueError(
            "SQLite workflow record exceeds "
            f"{MAX_SQLITE_WORKFLOW_RECORD_BYTES} bytes"
        )
    return raw.decode("utf-8")


def _encode_sqlite_trigger_response(response: Dict[str, object]) -> str:
    """Serialize one replay response within the durable byte boundary."""

    if not isinstance(response, dict):
        raise ValueError("SQLite trigger response must be an object")
    try:
        raw = json.dumps(
            response,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
        UnicodeError,
    ) as error:
        raise ValueError("SQLite trigger response is not JSON serializable") from error
    if len(raw) > MAX_SQLITE_TRIGGER_RESPONSE_BYTES:
        raise ValueError(
            "SQLite trigger response exceeds "
            f"{MAX_SQLITE_TRIGGER_RESPONSE_BYTES} bytes"
        )
    return raw.decode("utf-8")


def _encode_audit_event(event: AuditEvent) -> str:
    """Serialize one audit object within the shared UTF-8 event boundary."""

    if not isinstance(event, dict):
        raise ValueError("audit event must be an object")
    try:
        raw = json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8")
    except (
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
        UnicodeError,
    ) as error:
        raise ValueError("audit event is not JSON serializable") from error
    if len(raw) > MAX_AUDIT_EVENT_BYTES:
        raise ValueError(f"audit event exceeds {MAX_AUDIT_EVENT_BYTES} bytes")
    return raw.decode("utf-8")


def _iter_bounded_audit_lines(handle):
    """Yield JSONL audit lines without allocating an oversized line."""

    while True:
        line = handle.readline(MAX_AUDIT_EVENT_BYTES + 2)
        if not line:
            return
        # A writer emits one LF byte. Permit a legacy CRLF line only when the
        # event payload itself still fits the shared bound.
        if len(line) > MAX_AUDIT_EVENT_BYTES + 1:
            if not (
                len(line) == MAX_AUDIT_EVENT_BYTES + 2
                and line.endswith("\r\n")
            ):
                raise ValueError(f"audit event exceeds {MAX_AUDIT_EVENT_BYTES} bytes")
        elif len(line) == MAX_AUDIT_EVENT_BYTES + 1 and not line.endswith("\n"):
            raise ValueError(f"audit event exceeds {MAX_AUDIT_EVENT_BYTES} bytes")
        yield line


def _decode_audit_event(raw_event: object) -> AuditEvent:
    """Check one stored audit payload before JSON decoding it."""

    try:
        text = (
            raw_event.decode("utf-8")
            if isinstance(raw_event, bytes)
            else str(raw_event)
        ).rstrip("\r\n")
        encoded = text.encode("utf-8")
    except (TypeError, UnicodeError) as error:
        raise ValueError("audit event is not valid UTF-8") from error
    if len(encoded) > MAX_AUDIT_EVENT_BYTES:
        raise ValueError(f"audit event exceeds {MAX_AUDIT_EVENT_BYTES} bytes")
    try:
        event = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("audit event is not valid JSON") from error
    if not isinstance(event, dict):
        raise ValueError("audit event must be an object")
    return event


def _decode_sqlite_run_state(raw_state: object) -> RunState:
    """Decode one SQLite run state only after checking its UTF-8 byte bound."""

    try:
        encoded = str(raw_state).encode("utf-8")
    except UnicodeError as error:
        raise ValueError("SQLite run state is not valid UTF-8") from error
    if len(encoded) > MAX_SQLITE_RUN_STATE_BYTES:
        raise ValueError(
            f"SQLite run state exceeds {MAX_SQLITE_RUN_STATE_BYTES} bytes"
        )
    try:
        state = json.loads(encoded.decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("SQLite run state is not valid JSON") from error
    if not isinstance(state, dict):
        raise ValueError("SQLite run state must be an object")
    return state


def _decode_sqlite_workflow_record(raw_record: object) -> WorkflowRecord:
    """Decode one registry record only after checking its UTF-8 byte bound."""

    try:
        text = (
            raw_record.decode("utf-8")
            if isinstance(raw_record, bytes)
            else str(raw_record)
        )
        encoded = text.encode("utf-8")
    except (TypeError, UnicodeError) as error:
        raise ValueError("SQLite workflow record is not valid UTF-8") from error
    if len(encoded) > MAX_SQLITE_WORKFLOW_RECORD_BYTES:
        raise ValueError(
            "SQLite workflow record exceeds "
            f"{MAX_SQLITE_WORKFLOW_RECORD_BYTES} bytes"
        )
    try:
        record = json.loads(text)
    except (
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ) as error:
        raise ValueError("SQLite workflow record is not valid JSON") from error
    if not isinstance(record, dict):
        raise ValueError("SQLite workflow record must be an object")
    return record


def _decode_sqlite_trigger_response(raw_response: object) -> Dict[str, object]:
    """Decode one replay response only after checking its UTF-8 byte bound."""

    try:
        text = (
            raw_response.decode("utf-8")
            if isinstance(raw_response, bytes)
            else str(raw_response)
        )
        encoded = text.encode("utf-8")
    except (TypeError, UnicodeError) as error:
        raise ValueError("SQLite trigger response is not valid UTF-8") from error
    if len(encoded) > MAX_SQLITE_TRIGGER_RESPONSE_BYTES:
        raise ValueError(
            "SQLite trigger response exceeds "
            f"{MAX_SQLITE_TRIGGER_RESPONSE_BYTES} bytes"
        )
    try:
        response = json.loads(text)
    except (
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ) as error:
        raise ValueError("SQLite trigger response is not valid JSON") from error
    if not isinstance(response, dict):
        raise ValueError("SQLite trigger response must be an object")
    return response


def _read_bounded_json_document(path: Path, max_bytes: int, label: str):
    """Read one local JSON document through an identity-bound descriptor."""

    try:
        before = path.lstat()
    except OSError:
        raise
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError(f"{label} must be a regular non-symlink file")
    if before.st_size > max_bytes:
        raise ValueError(f"{label} exceeds {max_bytes} bytes")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise ValueError(f"{label} changed while being read")
        if opened.st_size > max_bytes:
            raise ValueError(f"{label} exceeds {max_bytes} bytes")

        chunks = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(
                descriptor,
                min(_JSON_RUN_STATE_READ_CHUNK_BYTES, remaining),
            )
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > max_bytes:
            raise ValueError(f"{label} exceeds {max_bytes} bytes")
        after = path.lstat()
        if after.st_dev != before.st_dev or after.st_ino != before.st_ino:
            raise ValueError(f"{label} changed while being read")
        if after.st_size > max_bytes:
            raise ValueError(f"{label} exceeds {max_bytes} bytes")
    finally:
        os.close(descriptor)
    return json.loads(raw.decode("utf-8"))


def _encode_json_run_state(state: RunState) -> bytes:
    """Serialize one JSON run state without exceeding the local file bound."""

    return _encode_bounded_json_document(
        state, MAX_JSON_RUN_STATE_BYTES, "JSON run state"
    )


def _read_json_run_state(path: Path) -> RunState:
    """Read one JSON run state through a bounded, identity-bound descriptor."""

    return _read_bounded_json_document(
        path, MAX_JSON_RUN_STATE_BYTES, "JSON run state"
    )


def _encode_json_control_index(index: Dict[str, WorkflowRecord]) -> bytes:
    """Serialize the JSON workflow index within its fixed local bound."""

    return _encode_bounded_json_document(
        index, MAX_JSON_CONTROL_INDEX_BYTES, "workflow index"
    )


def _read_json_control_index(path: Path):
    """Read the JSON workflow index through the bounded file contract."""

    return _read_bounded_json_document(
        path, MAX_JSON_CONTROL_INDEX_BYTES, "workflow index"
    )


def _validate_interrupted_recovery_limit(limit: int) -> None:
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_INTERRUPTED_RECOVERY_BATCH
    ):
        raise ValueError(
            "interrupted recovery limit must be an integer from 1 through "
            f"{MAX_INTERRUPTED_RECOVERY_BATCH}"
        )


def _validate_page_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("run page limit must be an integer from 1 through 100")


def _validate_snapshot_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("control snapshot limit must be an integer from 1 through 1000")


def _validate_run_list_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RUN_LIST_ITEMS:
        raise ValueError(f"run list limit must be an integer from 1 through {MAX_RUN_LIST_ITEMS}")


def _json_run_sort_key(state: RunState, path: Path):
    updated_at = state.get("updated_at")
    if not updated_at:
        events = state.get("events")
        if isinstance(events, list):
            for event in reversed(events):
                if isinstance(event, dict) and event.get("timestamp"):
                    updated_at = event["timestamp"]
                    break
    if updated_at:
        return (1, str(updated_at), str(state.get("run_id", path.stem)), path.name)
    try:
        fallback = f"{path.stat().st_mtime_ns:020d}"
    except OSError:
        fallback = ""
    return (0, fallback, str(state.get("run_id", path.stem)), path.name)


def _expire_waiting_workflow_state(state: RunState, now: str):
    if str(state.get("status", "")) != "waiting":
        return None
    execution = state.get("execution")
    if not isinstance(execution, dict):
        return None
    deadline_at = str(execution.get("workflow_deadline_at", ""))
    if not deadline_at:
        return None
    try:
        current_at = _parse_storage_timestamp(now)
        deadline = _parse_storage_timestamp(deadline_at)
        expired = current_at >= deadline
    except (TypeError, ValueError, OverflowError):
        expired = True
    if not expired:
        return None
    events = state.get("events", [])
    if not isinstance(events, list):
        events = []
    events.append(
        {
            "type": "run_failed",
            "node_id": str(state.get("current_node", "")),
            "timestamp": str(now),
            "error_code": "workflow_timeout",
            "timeout_ms": _positive_int(execution.get("workflow_timeout_ms")),
            "source": "deadline_sweeper",
        }
    )
    state["events"] = events
    state["status"] = "failed"
    state["error_code"] = "workflow_timeout"
    state["error"] = "workflow wall-clock deadline exceeded"
    execution["started_at"] = ""
    execution["deadline_at"] = ""
    execution["workflow_started_at"] = ""
    execution["workflow_deadline_at"] = ""
    return state


def _positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _parse_storage_timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _upsert_sqlite_state(connection, state: RunState) -> None:
    payload = _encode_sqlite_run_state(state)
    events = state.get("events", [])
    if not isinstance(events, list):
        events = []
    connection.execute(
        """
        insert into runs (
            run_id, workflow_id, workflow_version, status, current_node,
            state_json, updated_at
        ) values (?, ?, ?, ?, ?, ?, datetime('now'))
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
    _upsert_sqlite_summary(connection, state)
    connection.execute("delete from run_events where run_id = ?", (state["run_id"],))
    connection.executemany(
        """
        insert into run_events (
            run_id, sequence, event_type, node_id, timestamp, payload_json
        ) values (?, ?, ?, ?, ?, ?)
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


def _save_sqlite_state(connection, state: RunState) -> None:
    _upsert_sqlite_state(connection, state)


def _upsert_sqlite_summary(connection, state: RunState) -> None:
    """Maintain the compact projection used by bounded operator reads."""

    events = state.get("events", [])
    if not isinstance(events, list):
        events = []
    node_results = state.get("node_results", {})
    if not isinstance(node_results, dict):
        node_results = {}
    workflow = state.get("workflow", {})
    nodes = workflow.get("nodes", []) if isinstance(workflow, dict) else []
    node_ids = [
        str(node.get("id"))
        for node in nodes
        if isinstance(node, dict) and node.get("id")
    ]
    # Reuse the visualizer's established overlay semantics while persisting
    # only the allowlisted, value-free fields needed by run detail.  Importing
    # lazily keeps storage's low-level module boundary intact.
    from .visualizer import run_overlay_for_nodes

    overlays = run_overlay_for_nodes(node_ids, state, [])
    compact_overlays = {}
    for node_id, overlay in overlays.items():
        compact_overlays[str(node_id)] = {
            key: overlay.get(key)
            for key in (
                "node_id",
                "status",
                "current",
                "event_count",
                "latest_event_type",
                "result_status",
                "attempts",
                "max_attempts",
                "backoff_ms",
                "retry_count",
                "recovered",
                "connector_id",
                "connector_kind",
                "connector_status",
                "audit_event_count",
            )
        }
        compact_overlays[str(node_id)]["has_error"] = bool(overlay.get("error"))
    detail_projection = json.dumps(
        {"node_ids": node_ids, "node_overlays": compact_overlays},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    connection.execute(
        """
        insert into run_summaries (
            run_id, workflow_id, workflow_version, status, current_node,
            event_count, node_result_count, updated_at, detail_projection_json
        ) values (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        on conflict(run_id) do update set
            workflow_id = excluded.workflow_id,
            workflow_version = excluded.workflow_version,
            status = excluded.status,
            current_node = excluded.current_node,
            event_count = excluded.event_count,
            node_result_count = excluded.node_result_count,
            detail_projection_json = excluded.detail_projection_json,
            updated_at = excluded.updated_at
        """,
        (
            state["run_id"],
            state.get("workflow_id", "workflow"),
            state.get("workflow_version", "0.1.0"),
            state.get("status", "created"),
            state.get("current_node", ""),
            len(events),
            len(node_results),
            detail_projection,
        ),
    )


def _run_summary_from_row(row) -> RunState:
    return {
        "run_id": str(row[0]),
        "workflow_id": str(row[1]),
        "workflow_version": str(row[2]),
        "status": str(row[3]),
        "current_node": str(row[4]),
        "event_count": max(0, int(row[5])),
        "node_result_count": max(0, int(row[6])),
    }


def _run_summary_from_page_row(row) -> RunState:
    return {
        "run_id": str(row[0]),
        "workflow_id": str(row[2]),
        "workflow_version": str(row[3]),
        "status": str(row[4]),
        "current_node": str(row[5]),
        "event_count": max(0, int(row[6])),
        "node_result_count": max(0, int(row[7])),
    }


def _summarize_run_document(state: RunState) -> RunState:
    return {
        "run_id": state["run_id"],
        "workflow_id": state["workflow_id"],
        "workflow_version": state["workflow_version"],
        "status": state["status"],
        "current_node": state["current_node"],
        "event_count": len(state.get("events", [])),
        "node_result_count": len(state.get("node_results", {})),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
