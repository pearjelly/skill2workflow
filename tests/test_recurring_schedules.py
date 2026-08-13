from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import (
    RECURRING_SCHEDULE_SCHEMA_VERSION,
    LocalScheduleRunner,
    RecurringScheduleDispatcher,
    RecurringScheduleStore,
    normalize_recurring_schedule_definition,
)
from skill2workflow.triggers import MAX_TRIGGER_INPUT_BYTES


class RecurringScheduleContractTests(TestCase):
    def test_normalize_recurring_schedule_has_explicit_recovery_semantics(self):
        schedule = normalize_recurring_schedule_definition(_recurring_definition())

        self.assertEqual(schedule["schema_version"], RECURRING_SCHEDULE_SCHEMA_VERSION)
        self.assertEqual(
            schedule["schedule"],
            {
                "id": "schedule_hourly_report",
                "workflow_id": "workflow_recurring",
                "version": "1.0.0",
                "starts_at": "2026-08-11T00:00:00+00:00",
                "interval_seconds": 60,
                "missed_run_policy": "latest",
                "enabled": True,
                "status": "active",
                "next_run_at": "2026-08-11T00:00:00+00:00",
                "last_scheduled_for": "",
                "last_run_id": "",
                "last_trigger_id": "",
            },
        )
        self.assertEqual(
            schedule["trigger"],
            {
                "source": "recurring-schedule:schedule_hourly_report",
                "idempotency_key_prefix": "schedule_hourly_report",
                "input": {"report": "hourly"},
            },
        )

    def test_normalize_recurring_schedule_rejects_unsafe_or_ambiguous_contracts(self):
        cases = [
            ({}, "schema_version"),
            ({"schedule": {}}, "schema_version"),
            (_recurring_definition(interval_seconds=0), "interval_seconds"),
            (_recurring_definition(missed_run_policy="all"), "missed_run_policy"),
            (_recurring_definition(extra_schedule={"next_run_at": "2026-01-01T00:00:00Z"}), "unknown"),
        ]
        for payload, pattern in cases:
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(ValueError, pattern):
                    normalize_recurring_schedule_definition(payload)

        with self.assertRaisesRegex(ValueError, "recurring schedule trigger input exceeds"):
            normalize_recurring_schedule_definition(
                _recurring_definition(input_value={"payload": "x" * MAX_TRIGGER_INPUT_BYTES})
            )


class RecurringSchedulePersistenceTests(TestCase):
    def test_existing_schedule_cli_boundary_accepts_recurring_only_with_sqlite(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())
            runner = LocalScheduleRunner(state_dir, storage="sqlite")

            added = runner.add_schedule(_recurring_definition())
            result = runner.run_due("2026-08-11T00:00:00Z")
            listed = runner.list_schedules()
            dispatches = runner.list_dispatches()

            with self.assertRaisesRegex(ValueError, "requires sqlite"):
                LocalScheduleRunner(state_dir / "json", storage="json").add_schedule(
                    _recurring_definition()
                )

        self.assertEqual(added["schema_version"], RECURRING_SCHEDULE_SCHEMA_VERSION)
        self.assertEqual(result["count"], 1)
        self.assertEqual(listed[0]["schedule"]["next_run_at"], "2026-08-11T00:01:00+00:00")
        self.assertEqual(dispatches[0]["status"], "completed")

    def test_cli_due_run_honors_service_lease_before_any_sqlite_dispatch(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            runner = LocalScheduleRunner(state_dir, storage="sqlite")
            runner.add_schedule(
                {
                    "schema_version": "skill2workflow-schedule-0.1.0",
                    "schedule": {
                        "id": "one_shot_guarded",
                        "workflow_id": "workflow_recurring",
                        "version": "1.0.0",
                        "run_at": "2026-08-11T00:00:00Z",
                    },
                    "trigger": {"input": {}},
                }
            )
            owner = RecurringScheduleDispatcher(state_dir, owner_id="service-owner", lease_seconds=30)
            self.assertTrue(owner.try_acquire(now_epoch=1000))

            with self.assertRaisesRegex(ValueError, "lease is held"):
                runner.run_due("2026-08-11T00:00:00Z", lease_now_epoch=1001)

            runs = control.list_runs()

        self.assertEqual(runs, [])

    def test_sqlite_store_persists_definitions_and_dispatches_across_restart(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            store = RecurringScheduleStore(state_dir)
            stored = store.add(_recurring_definition())
            reloaded = RecurringScheduleStore(state_dir)
            reloaded_schedule = reloaded.get("schedule_hourly_report")
            dispatches = reloaded.list_dispatches()

        self.assertEqual(stored, reloaded_schedule)
        self.assertEqual(dispatches, [])

    def test_latest_policy_coalesces_missed_occurrences_into_one_durable_dispatch(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            store = RecurringScheduleStore(state_dir)
            store.add(_recurring_definition())
            dispatcher = RecurringScheduleDispatcher(state_dir, owner_id="owner-a", lease_seconds=30)
            self.assertTrue(dispatcher.try_acquire(now_epoch=1000))

            result = dispatcher.dispatch_due("2026-08-11T00:03:10Z", now_epoch=1001)
            second = dispatcher.dispatch_due("2026-08-11T00:03:10Z", now_epoch=1002)
            persisted = RecurringScheduleStore(state_dir).get("schedule_hourly_report")
            records = RecurringScheduleStore(state_dir).list_dispatches()

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["runs"][0]["scheduled_for"], "2026-08-11T00:03:00+00:00")
        self.assertEqual(result["runs"][0]["coalesced_occurrences"], 3)
        self.assertEqual(second["count"], 0)
        self.assertEqual(persisted["schedule"]["next_run_at"], "2026-08-11T00:04:00+00:00")
        self.assertEqual(records[0]["status"], "completed")
        self.assertEqual(records[0]["coalesced_occurrences"], 3)
        self.assertTrue(records[0]["run_id"].startswith("run_"))

    def test_skip_policy_records_missed_range_then_dispatches_next_occurrence(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            store = RecurringScheduleStore(state_dir)
            store.add(_recurring_definition(missed_run_policy="skip"))
            dispatcher = RecurringScheduleDispatcher(state_dir, owner_id="owner-a", lease_seconds=30)
            self.assertTrue(dispatcher.try_acquire(now_epoch=1000))

            missed = dispatcher.dispatch_due("2026-08-11T00:03:10Z", now_epoch=1001)
            next_result = dispatcher.dispatch_due("2026-08-11T00:04:00Z", now_epoch=1002)
            records = RecurringScheduleStore(state_dir).list_dispatches()

        self.assertEqual(missed["count"], 0)
        self.assertEqual(missed["skipped"], 4)
        self.assertEqual(next_result["count"], 1)
        self.assertEqual([record["status"] for record in records], ["skipped", "completed"])
        self.assertEqual(records[0]["coalesced_occurrences"], 4)

    def test_global_sqlite_lease_allows_only_one_dispatch_owner_and_clean_takeover(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            first = RecurringScheduleDispatcher(state_dir, owner_id="owner-a", lease_seconds=30)
            second = RecurringScheduleDispatcher(state_dir, owner_id="owner-b", lease_seconds=30)

            self.assertTrue(first.try_acquire(now_epoch=1000))
            self.assertFalse(second.try_acquire(now_epoch=1001))
            self.assertTrue(first.renew(now_epoch=1010))
            first.release()
            self.assertTrue(second.try_acquire(now_epoch=1011))

    def test_disable_and_reenable_are_durable_and_recovery_policy_handles_elapsed_time(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())
            store = RecurringScheduleStore(state_dir)
            store.add(_recurring_definition())
            disabled = store.set_enabled("schedule_hourly_report", False)
            dispatcher = RecurringScheduleDispatcher(state_dir, owner_id="owner-a", lease_seconds=30)
            self.assertTrue(dispatcher.try_acquire(now_epoch=1000))
            while_disabled = dispatcher.dispatch_due("2026-08-11T00:03:10Z", now_epoch=1001)
            enabled = store.set_enabled("schedule_hourly_report", True)
            after_enable = dispatcher.dispatch_due("2026-08-11T00:03:10Z", now_epoch=1002)

        self.assertEqual(disabled["schedule"]["status"], "disabled")
        self.assertEqual(while_disabled["count"], 0)
        self.assertEqual(enabled["schedule"]["status"], "active")
        self.assertEqual(after_enable["count"], 1)
        self.assertEqual(after_enable["runs"][0]["coalesced_occurrences"], 3)

    def test_stale_claim_becomes_uncertain_and_is_not_automatically_retried(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            store = RecurringScheduleStore(state_dir)
            store.add(_recurring_definition())
            first = RecurringScheduleDispatcher(state_dir, owner_id="owner-a", lease_seconds=5)
            self.assertTrue(first.try_acquire(now_epoch=1000))
            claimed = first.claim_due("2026-08-11T00:00:00Z", now_epoch=1001)
            second = RecurringScheduleDispatcher(state_dir, owner_id="owner-b", lease_seconds=5)

            self.assertTrue(second.try_acquire(now_epoch=1007))
            recovered = second.recover_stale_claims(now_epoch=1007)
            rerun = second.dispatch_due("2026-08-11T00:00:00Z", now_epoch=1008)
            records = RecurringScheduleStore(state_dir).list_dispatches()

        self.assertEqual(len(claimed), 1)
        self.assertEqual(recovered, 1)
        self.assertEqual(rerun["count"], 0)
        self.assertEqual(records[0]["status"], "uncertain")


def _recurring_definition(
    interval_seconds=60,
    missed_run_policy="latest",
    extra_schedule=None,
    input_value=None,
):
    schedule = {
        "id": "schedule_hourly_report",
        "workflow_id": "workflow_recurring",
        "version": "1.0.0",
        "starts_at": "2026-08-11T00:00:00Z",
        "interval_seconds": interval_seconds,
        "missed_run_policy": missed_run_policy,
    }
    schedule.update(extra_schedule or {})
    return {
        "schema_version": "skill2workflow-schedule-0.2.0",
        "schedule": schedule,
        "trigger": {"input": input_value if input_value is not None else {"report": "hourly"}},
    }


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_recurring",
            "name": "Recurring",
            "version": "1.0.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }
