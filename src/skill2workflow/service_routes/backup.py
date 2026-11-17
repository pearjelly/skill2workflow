"""Backup HTTP resource handlers; transport policy stays in dispatch."""

from __future__ import annotations

from .. import service as service_module


class BackupRoutes:
    def _handle_backup_readiness(self):
        """Serve fixed read-only preflight data for an offline backup."""

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
                {"error": "backup readiness request must not include a body"},
            )
            return
        try:
            payload = service_module.build_state_backup_readiness_report(self.runtime_service.config.state_dir)
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_BACKUP_READINESS_RESPONSE_BYTES:
                raise ValueError("backup readiness exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "backup readiness unavailable"})
            return
        self._send_json(200, payload)

    def _handle_backup_inventory(self):
        """Serve a bounded, redacted inventory of configured backups."""

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
            query = service_module._backup_inventory_query(self.path)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        if content_length != 0:
            self._send_json(
                400,
                {"error": "backup inventory request must not include a body"},
            )
            return
        parent_dir = self.runtime_service.config.backup_parent_dir
        if parent_dir is None:
            self._send_json(503, {"error": "backup inventory unavailable"})
            return
        try:
            payload = service_module.build_remote_backup_inventory(
                parent_dir,
                max_items=query["max_items"],
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_REMOTE_BACKUP_INVENTORY_RESPONSE_BYTES:
                raise ValueError("backup inventory exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "backup inventory unavailable"})
            return
        self._send_json(200, payload)

    def _handle_backup_inventory_page(self):
        """Serve one cursor-paged, redacted inventory of configured backups."""

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
            query = service_module._backup_inventory_page_query(self.path)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        if content_length != 0:
            self._send_json(
                400,
                {"error": "backup inventory page request must not include a body"},
            )
            return
        parent_dir = self.runtime_service.config.backup_parent_dir
        if parent_dir is None:
            self._send_json(503, {"error": "backup inventory page unavailable"})
            return
        try:
            payload = service_module.build_remote_backup_inventory_page(
                parent_dir,
                max_items=query["max_items"],
                cursor=query["cursor"],
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_REMOTE_BACKUP_INVENTORY_PAGE_RESPONSE_BYTES:
                raise ValueError("backup inventory page exceeds response limit")
        except ValueError as error:
            if "cursor is invalid" in str(error):
                self._send_json(400, {"error": "backup inventory page cursor is invalid"})
            else:
                self._send_json(503, {"error": "backup inventory page unavailable"})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "backup inventory page unavailable"})
            return
        self._send_json(200, payload)

    def _handle_retention_readiness(self):
        """Serve a policy-bound, read-only retention preflight."""

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
            body = service_module.read_request_body(self)
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"policy"}
                or not isinstance(payload.get("policy"), dict)
            ):
                raise ValueError(
                    "retention readiness request must contain one policy object"
                )
            policy = service_module.normalize_retention_policy(payload["policy"])
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        except (
            UnicodeDecodeError,
            service_module.json.JSONDecodeError,
            TypeError,
            ValueError,
            OverflowError,
            RecursionError,
        ):
            self._send_json(400, {"error": "retention readiness rejected"})
            return
        try:
            report = service_module.build_state_retention_readiness_report(
                self.runtime_service.config.state_dir,
                policy,
            )
            encoded = service_module.json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_RETENTION_READINESS_RESPONSE_BYTES:
                raise ValueError("retention readiness exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "retention readiness unavailable"})
            return
        self._send_json(200, report)

    def _handle_backup_retention_plan(self):
        """Serve a redacted, policy-bound backup expiration plan."""

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
            body = service_module.read_request_body(self)
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"policy"}
                or not isinstance(payload.get("policy"), dict)
            ):
                raise ValueError(
                    "backup retention plan request must contain one policy object"
                )
            policy = service_module.normalize_backup_retention_policy(payload["policy"])
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        except (
            UnicodeDecodeError,
            service_module.json.JSONDecodeError,
            TypeError,
            ValueError,
            OverflowError,
            RecursionError,
        ):
            self._send_json(400, {"error": "backup retention plan rejected"})
            return
        parent_dir = self.runtime_service.config.backup_parent_dir
        if parent_dir is None:
            self._send_json(503, {"error": "backup retention plan unavailable"})
            return
        try:
            report = service_module.build_remote_backup_retention_plan(parent_dir, policy)
            encoded = service_module.json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_REMOTE_BACKUP_RETENTION_PLAN_RESPONSE_BYTES:
                raise ValueError("backup retention plan exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "backup retention plan unavailable"})
            return
        self._send_json(200, report)
