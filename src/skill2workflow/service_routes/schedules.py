"""Schedules HTTP resource handlers; transport policy stays in dispatch."""

from __future__ import annotations

from .. import service as service_module


class ScheduleRoutes:
    def _handle_recurring_schedule_create(self):
        """Create or replay one authenticated recurring schedule."""

        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            self.runtime_service.control_plane.record_ingress_authentication(
                False,
                self.command,
                "recurring_schedule_create",
                reason=reason,
            )
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        self.runtime_service.control_plane.record_ingress_authentication(
            True,
            self.command,
            "recurring_schedule_create",
        )
        try:
            body = service_module.read_request_body(self)
            if not body:
                raise ValueError("recurring schedule create body must contain schedule")
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"schedule"}
                or not isinstance(payload.get("schedule"), dict)
            ):
                raise ValueError("recurring schedule create body must contain schedule")
            definition, created = (
                self.runtime_service.scheduler.dispatcher.store.add_with_result(
                    payload["schedule"]
                )
            )
            self.runtime_service.control_plane.record_recurring_schedule_created(
                str(definition["schedule"]["id"]),
                created,
            )
            response = service_module.build_recurring_schedule_create_response(
                definition,
                created=created,
            )
            encoded = service_module.json.dumps(response, ensure_ascii=False).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_CREATE_RESPONSE_BYTES:
                raise ValueError("recurring schedule create exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "recurring schedule create body must be valid JSON"},
            )
        except ValueError as error:
            message = str(error)
            if "already exists" in message:
                self._send_json(
                    409,
                    {"error": "recurring schedule already exists"},
                )
            elif "body must" in message:
                self._send_json(400, {"error": message})
            else:
                self._send_json(
                    400,
                    {"error": "recurring schedule definition rejected"},
                )
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule create unavailable"})

    def _handle_recurring_schedule_list(self):
        """Serve a bounded, redacted recurring-schedule inventory."""

        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        try:
            content_length = service_module._content_length(self)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        if content_length != 0:
            self._send_json(
                400,
                {"error": "recurring schedule list request must not include a body"},
            )
            return
        try:
            payload = service_module.build_recurring_schedule_list_from_store(
                self.runtime_service.scheduler.dispatcher.store,
                max_items=service_module.MAX_RECURRING_SCHEDULE_LIST_ITEMS,
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_LIST_RESPONSE_BYTES:
                raise ValueError("recurring schedule list exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule list unavailable"})
            return
        self._send_json(200, payload)

    def _handle_recurring_schedule_update(self, schedule_id: str):
        """Update one recurring definition with a progress CAS guard."""

        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            self.runtime_service.control_plane.record_ingress_authentication(
                False,
                self.command,
                "recurring_schedule_update",
                reason=reason,
            )
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        self.runtime_service.control_plane.record_ingress_authentication(
            True,
            self.command,
            "recurring_schedule_update",
        )
        try:
            body = service_module.read_request_body(self)
            if not body:
                raise ValueError(
                    "recurring schedule update body must contain schedule and expected_next_run_at"
                )
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"schedule", "expected_next_run_at"}
                or not isinstance(payload.get("schedule"), dict)
                or not isinstance(payload.get("expected_next_run_at"), str)
                or not payload.get("expected_next_run_at")
            ):
                raise ValueError(
                    "recurring schedule update body must contain schedule and expected_next_run_at"
                )
            definition, changed = self.runtime_service.scheduler.dispatcher.store.update_with_result(
                schedule_id,
                payload["schedule"],
                expected_next_run_at=payload["expected_next_run_at"],
            )
            self.runtime_service.control_plane.record_recurring_schedule_definition_updated(
                schedule_id,
                changed,
            )
            response = service_module.build_recurring_schedule_update_response(
                definition,
                changed=changed,
            )
            encoded = service_module.json.dumps(response, ensure_ascii=False).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_UPDATE_RESPONSE_BYTES:
                raise ValueError("recurring schedule update exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "recurring schedule update body must be valid JSON"},
            )
        except ValueError as error:
            message = str(error)
            if "not found" in message:
                self._send_json(404, {"error": "recurring schedule not found"})
            elif "precondition failed" in message:
                self._send_json(
                    409,
                    {"error": "recurring schedule update precondition failed"},
                )
            elif "body must" in message:
                self._send_json(400, {"error": message})
            else:
                self._send_json(
                    400,
                    {"error": "recurring schedule definition rejected"},
                )
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule update unavailable"})

    def _handle_recurring_schedule_patch(self, schedule_id: str):
        """Patch safe recurring fields while preserving trigger metadata."""

        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            self.runtime_service.control_plane.record_ingress_authentication(
                False,
                self.command,
                "recurring_schedule_patch",
                reason=reason,
            )
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        self.runtime_service.control_plane.record_ingress_authentication(
            True,
            self.command,
            "recurring_schedule_patch",
        )
        try:
            body = service_module.read_request_body(self)
            if not body:
                raise ValueError(
                    "recurring schedule patch body must contain schedule and expected_next_run_at"
                )
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"schedule", "expected_next_run_at"}
                or not isinstance(payload.get("schedule"), dict)
                or not isinstance(payload.get("expected_next_run_at"), str)
                or not payload.get("expected_next_run_at")
            ):
                raise ValueError(
                    "recurring schedule patch body must contain schedule and expected_next_run_at"
                )
            definition, changed = self.runtime_service.scheduler.dispatcher.store.patch_with_result(
                schedule_id,
                payload["schedule"],
                expected_next_run_at=payload["expected_next_run_at"],
            )
            self.runtime_service.control_plane.record_recurring_schedule_patched(
                schedule_id,
                changed,
            )
            response = service_module.build_recurring_schedule_patch_response(
                definition,
                changed=changed,
            )
            encoded = service_module.json.dumps(response, ensure_ascii=False).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_PATCH_RESPONSE_BYTES:
                raise ValueError("recurring schedule patch exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "recurring schedule patch body must be valid JSON"},
            )
        except ValueError as error:
            message = str(error)
            if "not found" in message:
                self._send_json(404, {"error": "recurring schedule not found"})
            elif "precondition failed" in message:
                self._send_json(
                    409,
                    {"error": "recurring schedule patch precondition failed"},
                )
            elif "body must" in message:
                self._send_json(400, {"error": message})
            else:
                self._send_json(
                    400,
                    {"error": "recurring schedule patch rejected"},
                )
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule patch unavailable"})

    def _handle_recurring_schedule_delete(self, schedule_id: str):
        """Retire one authenticated recurring schedule safely."""

        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            self.runtime_service.control_plane.record_ingress_authentication(
                False,
                self.command,
                "recurring_schedule_delete",
                reason=reason,
            )
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        self.runtime_service.control_plane.record_ingress_authentication(
            True,
            self.command,
            "recurring_schedule_delete",
        )
        try:
            body = service_module.read_request_body(self)
            if not body:
                raise ValueError(
                    "recurring schedule delete body must contain expected_next_run_at and confirm"
                )
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"expected_next_run_at", "confirm"}
                or not isinstance(payload.get("expected_next_run_at"), str)
                or not payload.get("expected_next_run_at")
                or payload.get("confirm") is not True
            ):
                raise ValueError(
                    "recurring schedule delete body must contain expected_next_run_at and confirm"
                )
            deleted = self.runtime_service.scheduler.dispatcher.store.delete_with_result(
                schedule_id,
                expected_next_run_at=payload["expected_next_run_at"],
            )
            self.runtime_service.control_plane.record_recurring_schedule_deleted(
                schedule_id,
                deleted,
            )
            response = service_module.build_recurring_schedule_delete_response(
                schedule_id,
                deleted=deleted,
            )
            encoded = service_module.json.dumps(response, ensure_ascii=False).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_DELETE_RESPONSE_BYTES:
                raise ValueError("recurring schedule delete exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "recurring schedule delete body must be valid JSON"},
            )
        except ValueError as error:
            message = str(error)
            if "not found" in message:
                self._send_json(404, {"error": "recurring schedule not found"})
            elif "precondition failed" in message:
                self._send_json(
                    409,
                    {"error": "recurring schedule delete precondition failed"},
                )
            elif "must be disabled" in message:
                self._send_json(
                    409,
                    {"error": "recurring schedule must be disabled before deletion"},
                )
            elif "active dispatch" in message:
                self._send_json(
                    409,
                    {"error": "recurring schedule has active dispatch"},
                )
            elif "body must" in message:
                self._send_json(400, {"error": message})
            else:
                self._send_json(
                    400,
                    {"error": "recurring schedule deletion rejected"},
                )
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule delete unavailable"})

    def _handle_recurring_schedule_action(self, schedule_id: str, enabled: bool):
        """Apply one authenticated, idempotent recurring-schedule state change."""

        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            self.runtime_service.control_plane.record_ingress_authentication(
                False,
                self.command,
                "recurring_schedule_action",
                reason=reason,
            )
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        self.runtime_service.control_plane.record_ingress_authentication(
            True,
            self.command,
            "recurring_schedule_action",
        )
        try:
            body = service_module.read_request_body(self)
            if not body:
                raise ValueError(
                    "recurring schedule action body must be an empty JSON object"
                )
            payload = service_module.json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) not in (
                set(),
                {"expected_next_run_at"},
            ):
                raise ValueError(
                    "recurring schedule action body must be an empty JSON object"
                )
            has_expected_next_run_at = "expected_next_run_at" in payload
            expected_next_run_at = payload.get("expected_next_run_at")
            if has_expected_next_run_at and (
                not isinstance(expected_next_run_at, str)
                or not expected_next_run_at
                or len(expected_next_run_at) > 64
                or any(
                    ord(char) < 0x20 or ord(char) == 0x7F
                    for char in expected_next_run_at
                )
            ):
                raise ValueError(
                    "expected_next_run_at must be a non-empty timestamp"
                )
            state_kwargs = {}
            if has_expected_next_run_at:
                state_kwargs["expected_next_run_at"] = expected_next_run_at
            definition, changed = self.runtime_service.scheduler.dispatcher.store.set_enabled_with_result(
                schedule_id,
                enabled,
                **state_kwargs,
            )
            self.runtime_service.control_plane.record_recurring_schedule_change(
                schedule_id,
                enabled,
                changed,
            )
            response = {
                "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
                "schedule_id": schedule_id,
                "enabled": bool(definition["schedule"]["enabled"]),
                "status": str(definition["schedule"]["status"]),
                "changed": changed,
            }
            encoded = service_module.json.dumps(response, ensure_ascii=False).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_ACTION_RESPONSE_BYTES:
                raise ValueError("recurring schedule action exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "recurring schedule action body must be valid JSON"},
            )
        except ValueError as error:
            if "recurring schedule not found" in str(error):
                self._send_json(404, {"error": "recurring schedule not found"})
            elif "precondition failed" in str(error):
                self._send_json(
                    409,
                    {"error": "recurring schedule action precondition failed"},
                )
            elif "expected_next_run_at" in str(error):
                self._send_json(400, {"error": str(error)})
            elif "body must" in str(error):
                self._send_json(400, {"error": str(error)})
            else:
                self._send_json(503, {"error": "recurring schedule action unavailable"})
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule action unavailable"})

    def _handle_recurring_schedule_dispatch_review(
        self,
        dispatch_id: str,
        *,
        write: bool,
    ):
        """Read or persist one explicit review of an uncertain dispatch."""

        if write:
            readiness_status, _ = self.runtime_service.readiness()
            if readiness_status != 200:
                self._send_json(503, {"error": "service is not ready"})
                return
        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            self.runtime_service.control_plane.record_ingress_authentication(
                False,
                self.command,
                "recurring_schedule_dispatch_review",
                reason=reason,
            )
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        self.runtime_service.control_plane.record_ingress_authentication(
            True,
            self.command,
            "recurring_schedule_dispatch_review",
        )
        try:
            if write:
                body = service_module.read_request_body(self)
                if not body:
                    raise ValueError(
                        "recurring dispatch review body must contain expected_completed_at and outcome"
                    )
                payload = service_module.json.loads(body.decode("utf-8"))
                if (
                    not isinstance(payload, dict)
                    or set(payload) != {"expected_completed_at", "outcome"}
                    or not isinstance(payload.get("expected_completed_at"), str)
                    or not isinstance(payload.get("outcome"), str)
                ):
                    raise ValueError(
                        "recurring dispatch review body must contain expected_completed_at and outcome"
                    )
                review, changed = (
                    self.runtime_service.scheduler.dispatcher.store.review_uncertain_dispatch_with_result(
                        dispatch_id,
                        expected_completed_at=payload["expected_completed_at"],
                        outcome=payload["outcome"],
                    )
                )
                self.runtime_service.control_plane.record_recurring_schedule_dispatch_review(
                    dispatch_id,
                    str(review["schedule_id"]),
                    str(review["outcome"]),
                    changed,
                )
            else:
                content_length = service_module._content_length(self)
                if content_length != 0:
                    self._send_json(
                        400,
                        {
                            "error": "recurring dispatch review request must not include a body"
                        },
                    )
                    return
                review = self.runtime_service.scheduler.dispatcher.store.get_dispatch_review(
                    dispatch_id
                )
                changed = False
            response = service_module.build_recurring_schedule_dispatch_review_response(
                review,
                changed=changed,
            )
            encoded = service_module.json.dumps(response, ensure_ascii=False).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_DISPATCH_REVIEW_RESPONSE_BYTES:
                raise ValueError("recurring dispatch review exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "recurring dispatch review body must be valid JSON"},
            )
        except ValueError as error:
            message = str(error)
            if "not found" in message:
                self._send_json(404, {"error": "recurring dispatch review not found"})
            elif (
                "precondition failed" in message
                or "not uncertain" in message
                or "already exists" in message
            ):
                self._send_json(409, {"error": "recurring dispatch review conflict"})
            elif "body must" in message or "outcome must" in message or "timestamp" in message:
                self._send_json(400, {"error": message})
            else:
                self._send_json(503, {"error": "recurring dispatch review unavailable"})
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring dispatch review unavailable"})

    def _handle_recurring_schedule_dispatch_list(self, schedule_id: str):
        """Serve bounded, redacted recurring dispatch evidence."""

        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        try:
            content_length = service_module._content_length(self)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        if content_length != 0:
            self._send_json(
                400,
                {"error": "recurring schedule dispatch list request must not include a body"},
            )
            return
        try:
            payload = service_module.build_recurring_schedule_dispatch_list_from_store(
                self.runtime_service.scheduler.dispatcher.store,
                schedule_id=schedule_id,
                max_items=service_module.MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS,
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_DISPATCH_LIST_RESPONSE_BYTES:
                raise ValueError("recurring schedule dispatch list exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule dispatch list unavailable"})
            return
        self._send_json(200, payload)

    def _handle_recurring_schedule_dispatch_page(self, schedule_id: str):
        """Serve a cursor-paged, redacted recurring dispatch projection."""

        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        if not authenticated:
            status_code = 503 if reason == "provider_unavailable" else 401
            self._send_json(
                status_code,
                {
                    "error": "authentication unavailable"
                    if status_code == 503
                    else "authentication required"
                },
                headers={"WWW-Authenticate": "Bearer"}
                if status_code == 401
                else None,
            )
            return
        try:
            content_length = service_module._content_length(self)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        if content_length != 0:
            self._send_json(
                400,
                {"error": "recurring schedule dispatch page request must not include a body"},
            )
            return
        try:
            query = service_module._recurring_schedule_dispatch_page_query(self.path)
            payload = service_module.build_recurring_schedule_dispatch_page_from_store(
                self.runtime_service.scheduler.dispatcher.store,
                schedule_id=schedule_id,
                max_items=query["max_items"],
                cursor=query["cursor"],
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RECURRING_SCHEDULE_DISPATCH_PAGE_RESPONSE_BYTES:
                raise ValueError("recurring schedule dispatch page exceeds response limit")
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "recurring schedule dispatch page unavailable"})
            return
        self._send_json(200, payload)
