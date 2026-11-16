"""Ops HTTP resource handlers; transport policy stays in dispatch."""

from __future__ import annotations

from .. import service as service_module


class OpsRoutes:
    def _handle_metrics(self):
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
                headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
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
                {"error": "metrics request must not include a body"},
            )
            return
        readiness_status, _ = self.runtime_service.readiness()
        try:
            lease_owned = self.runtime_service.scheduler.dispatcher.has_lease(now_epoch=service_module.time.time())
            payload = self.runtime_service.telemetry.render(
                service_status=self.runtime_service.status,
                ready=readiness_status == 200,
                scheduler_lease_owned=lease_owned,
            )
        except (OSError, service_module.sqlite3.Error, ValueError):
            self._send_json(503, {"error": "metrics unavailable"})
            return
        self._send_text(200, payload)

    def _handle_control_snapshot(self):
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
                {"error": "live control snapshot request must not include a body"},
            )
            return
        try:
            snapshot = service_module.build_control_snapshot_from_control(
                self.runtime_service.control_plane,
                max_items=service_module.LIVE_CONTROL_SNAPSHOT_MAX_ITEMS,
            )
            snapshot_size = len(
                service_module.json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")
            )
            if snapshot_size > service_module.MAX_LIVE_CONTROL_SNAPSHOT_BYTES:
                raise ValueError("control snapshot exceeds response limit")
        except ValueError:
            self._send_json(503, {"error": "control snapshot unavailable"})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "control snapshot unavailable"})
            return
        self._send_json(200, snapshot)

    def _handle_audit_event_page(self):
        """Serve a bounded, redacted, cursor-paged audit event projection."""

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
                {"error": "audit event page request must not include a body"},
            )
            return
        try:
            query = service_module._audit_event_page_query(self.path)
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        try:
            payload = service_module.build_audit_event_page_from_control(
                self.runtime_service.control_plane,
                max_items=query["max_items"],
                cursor=query["cursor"],
                workflow_id=query["workflow_id"],
                workflow_version=query["workflow_version"],
                run_id=query["run_id"],
                event_type=query["event_type"],
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_AUDIT_EVENT_LIST_RESPONSE_BYTES:
                raise ValueError("audit event page exceeds response limit")
        except ValueError:
            self._send_json(503, {"error": "audit event page unavailable"})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "audit event page unavailable"})
            return
        self._send_json(200, payload)

    def _handle_operational_readiness(self):
        """Serve one aggregate, redacted operator readiness report."""

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
                {"error": "operational readiness request must not include a body"},
            )
            return
        try:
            report = service_module.build_operational_readiness_report(self.runtime_service)
            if report.get("schema_version") != service_module.OPERATIONAL_READINESS_SCHEMA_VERSION:
                raise ValueError("operational readiness schema is invalid")
            encoded = service_module.json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_OPERATIONAL_READINESS_RESPONSE_BYTES:
                raise ValueError("operational readiness exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "operational readiness unavailable"})
            return
        self._send_json(200, report)

    def _handle_audit_integrity(self):
        """Serve the fixed, payload-free SQLite audit-chain result."""

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
                {"error": "audit integrity request must not include a body"},
            )
            return
        try:
            payload = self.runtime_service.control_plane.verify_audit_integrity()
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_AUDIT_INTEGRITY_RESPONSE_BYTES:
                raise ValueError("audit integrity exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "audit integrity unavailable"})
            return
        self._send_json(200, payload)

    def _handle_runtime_info(self):
        """Serve fixed runtime identity and compatibility metadata."""

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
                {"error": "runtime info request must not include a body"},
            )
            return
        try:
            readiness_status, _ = self.runtime_service.readiness()
            payload = {
                "schema_version": service_module.RUNTIME_INFO_SCHEMA_VERSION,
                "package_version": service_module.__version__,
                "compatibility_line": "0.1.x",
                "service_schema_version": service_module.SERVICE_SCHEMA_VERSION,
                "workflow_dsl_schema_version": service_module.WORKFLOW_DSL_SCHEMA_VERSION,
                "storage": self.runtime_service.config.storage,
                "state_layout_version": service_module.inspect_state_layout(
                    self.runtime_service.config.state_dir
                ),
                "service_status": self.runtime_service.status,
                "service_ready": readiness_status == 200,
                "scheduler_lease_owned": bool(
                    self.runtime_service.scheduler.dispatcher.has_lease(now_epoch=service_module.time.time())
                ),
            }
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RUNTIME_INFO_RESPONSE_BYTES:
                raise ValueError("runtime info exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "runtime info unavailable"})
            return
        self._send_json(200, payload)

    def _handle_audit_consistency(self, run_id: str = ""):
        """Serve the bounded, value-free run/audit consistency projection."""

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
                {"error": "audit consistency request must not include a body"},
            )
            return
        try:
            payload = self.runtime_service.control_plane.inspect_run_audit(run_id=run_id)
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES:
                raise ValueError("audit consistency exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "audit consistency unavailable"})
            return
        self._send_json(200, payload)

    def _handle_support_bundle(self):
        """Serve one bounded, redacted diagnostic package."""

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
                {"error": "support bundle request must not include a body"},
            )
            return
        try:
            readiness_status, _ = self.runtime_service.readiness()
            lease_owned = self.runtime_service.scheduler.dispatcher.has_lease(now_epoch=service_module.time.time())
            payload = service_module.build_support_bundle_from_control(
                self.runtime_service.control_plane,
                self.runtime_service.telemetry,
                service_status=self.runtime_service.status,
                ready=readiness_status == 200,
                scheduler_lease_owned=lease_owned,
                storage=self.runtime_service.config.storage,
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_SUPPORT_BUNDLE_BYTES:
                raise ValueError("support bundle exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "support bundle unavailable"})
            return
        self._send_json(200, payload)

    def _handle_health(self):
        self._send_json(200, {"service": "skill2workflow", "status": "ok"})

    def _handle_ready(self):
        status_code, payload = self.runtime_service.readiness()
        self._send_json(status_code, payload)
