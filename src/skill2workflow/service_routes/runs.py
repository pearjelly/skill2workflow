"""Runs HTTP resource handlers; transport policy stays in dispatch."""

from __future__ import annotations

from .. import service as service_module


class RunRoutes:
    def _handle_run_detail(self, run_id: str):
        """Serve a bounded status projection for one authenticated run."""

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
                {"error": "run detail request must not include a body"},
            )
            return
        try:
            detail = service_module.build_run_detail_from_control(
                self.runtime_service.control_plane,
                run_id,
                max_events=service_module.MAX_RUN_DETAIL_EVENTS,
            )
            encoded = service_module.json.dumps(detail, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RUN_DETAIL_RESPONSE_BYTES:
                raise ValueError("run detail exceeds response limit")
        except FileNotFoundError:
            self._send_json(404, {"error": "run not found"})
            return
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "run detail unavailable"})
            return
        self._send_json(200, detail)

    def _handle_run_list(self):
        """Serve a bounded, redacted list for run discovery."""

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
            self._send_json(400, {"error": "run list request must not include a body"})
            return
        try:
            payload = service_module.build_run_list_from_control(
                self.runtime_service.control_plane,
                max_items=service_module.MAX_RUN_LIST_ITEMS,
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RUN_LIST_RESPONSE_BYTES:
                raise ValueError("run list exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "run list unavailable"})
            return
        self._send_json(200, payload)

    def _handle_run_page(self):
        """Serve a filtered, cursor-paged redacted run projection."""

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
            self._send_json(400, {"error": "run page request must not include a body"})
            return
        try:
            query = service_module._run_page_query(self.path)
            payload = service_module.build_run_page_from_control(
                self.runtime_service.control_plane,
                max_items=query["max_items"],
                cursor=query["cursor"],
                status=query["status"],
                workflow_id=query["workflow_id"],
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RUN_PAGE_RESPONSE_BYTES:
                raise ValueError("run page exceeds response limit")
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "run page unavailable"})
            return
        self._send_json(200, payload)

    def _handle_webhook(self):
        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
        authenticated, reason = self.runtime_service.authenticator.authenticate(
            self.headers.get("Authorization", "")
        )
        route = service_module._request_route(self.command, service_module.urlsplit(self.path).path)
        if not authenticated:
            self.runtime_service.control_plane.record_ingress_authentication(
                False,
                self.command,
                route,
                reason=reason,
            )
            status_code = 503 if reason == "provider_unavailable" else 401
            error_message = (
                "authentication unavailable"
                if status_code == 503
                else "authentication required"
            )
            self._send_json(
                status_code,
                {"error": error_message},
                headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
            )
            return
        self.runtime_service.control_plane.record_ingress_authentication(
            True,
            self.command,
            route,
        )
        try:
            body = service_module.read_request_body(self)
            payload = service_module.handle_webhook_request(
                self.runtime_service.control_plane,
                self.command,
                self.path,
                body,
            )
            self._send_json(200, payload)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except service_module.TriggerIdempotencyError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except ValueError as error:
            self._send_json(400, {"error": str(error)})

    def _handle_cancel(self, run_id: str):
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
                "run_cancel",
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
            "run_cancel",
        )
        try:
            body = service_module.read_request_body(self)
            if not body:
                raise ValueError("run cancellation body must be an empty JSON object")
            payload = service_module.json.loads(body.decode("utf-8"))
            if payload != {}:
                raise ValueError("run cancellation body must be an empty JSON object")
            state = self.runtime_service.control_plane.cancel_published_run(run_id)
            self._send_json(
                200,
                {"run_id": run_id, "status": str(state["status"])},
            )
        except FileNotFoundError:
            self._send_json(404, {"error": "run not found"})
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(400, {"error": "run cancellation body must be valid JSON"})
        except ValueError as error:
            status_code = (
                409
                if any(
                    phrase in str(error)
                    for phrase in (
                        "already completed",
                        "already failed",
                        "already interrupted",
                    )
                )
                else 400
            )
            self._send_json(status_code, {"error": str(error)})

    def _handle_resume(self, run_id: str):
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
                "run_resume",
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
            "run_resume",
        )
        try:
            body = service_module.read_request_body(self)
            if not body:
                raise ValueError("run resume body must contain approved boolean")
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"approved"}
                or not isinstance(payload["approved"], bool)
            ):
                raise ValueError("run resume body must contain approved boolean")
            state = self.runtime_service.control_plane.resume_published_run(
                run_id,
                approved=payload["approved"],
            )
            self._send_json(
                200,
                {
                    "run_id": run_id,
                    "status": str(state["status"]),
                    "approved": payload["approved"],
                },
            )
        except FileNotFoundError:
            self._send_json(404, {"error": "run not found"})
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "run resume body must contain approved boolean"},
            )
        except ValueError as error:
            if str(error).startswith(f"run {run_id} "):
                self._send_json(409, {"error": "run is not waiting"})
            else:
                self._send_json(400, {"error": str(error)})
