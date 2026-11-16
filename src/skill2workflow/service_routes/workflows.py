"""Workflows HTTP resource handlers; transport policy stays in dispatch."""

from __future__ import annotations

from .. import service as service_module


class WorkflowRoutes:
    def _handle_workflow_artifact_report(self):
        """Serve a bounded, value-free workflow artifact report."""

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
                {"error": "workflow artifact report request must not include a body"},
            )
            return
        try:
            payload = service_module.build_workflow_artifact_report_from_control(
                self.runtime_service.control_plane,
                max_issues=service_module.MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES,
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_ARTIFACT_REPORT_RESPONSE_BYTES:
                raise ValueError("workflow artifact report exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow artifact report unavailable"})
            return
        self._send_json(200, payload)

    def _handle_workflow_inventory(self):
        """Serve bounded published-version metadata without workflow content."""

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
                {"error": "workflow inventory request must not include a body"},
            )
            return
        try:
            payload = service_module.build_workflow_inventory_from_control(
                self.runtime_service.control_plane,
                max_items=service_module.MAX_WORKFLOW_INVENTORY_ITEMS,
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_INVENTORY_RESPONSE_BYTES:
                raise ValueError("workflow inventory exceeds response limit")
        except (ValueError, OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow inventory unavailable"})
            return
        self._send_json(200, payload)

    def _handle_workflow_explanation(self, parts):
        """Serve a bounded, side-effect-free explanation of one version."""

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
                {"error": "workflow explanation request must not include a body"},
            )
            return
        workflow_id, version = parts
        try:
            payload = service_module.build_workflow_explanation(
                self.runtime_service.control_plane.get_workflow(workflow_id, version)
            )
            encoded = service_module.json.dumps(
                payload, ensure_ascii=False, indent=2
            ).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_EXPLANATION_RESPONSE_BYTES:
                raise ValueError("workflow explanation exceeds response limit")
        except ValueError as error:
            message = str(error).lower()
            if "version not found" in message:
                self._send_json(404, {"error": "workflow version not found"})
            else:
                self._send_json(503, {"error": "workflow explanation unavailable"})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow explanation unavailable"})
            return
        self._send_json(200, payload)

    def _handle_workflow_preflight(self, parts):
        """Serve a bounded trigger preflight without executing the workflow."""

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
            payload = service_module.json.loads(body.decode("utf-8")) if body else {}
            if not isinstance(payload, dict) or set(payload) not in ({}, {"input"}):
                raise ValueError("workflow preflight request must contain an optional input object")
            input_present = "input" in payload
            if input_present and not isinstance(payload.get("input"), dict):
                raise ValueError("workflow preflight request input must be an object")
            if input_present and len(payload["input"]) > service_module.MAX_WORKFLOW_PREFLIGHT_INPUT_KEYS:
                raise ValueError("workflow preflight request input has too many properties")
            if input_present:
                payload["input"] = service_module.normalize_preflight_input(payload["input"])
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        except (UnicodeDecodeError, service_module.json.JSONDecodeError, TypeError, ValueError, OverflowError, RecursionError):
            self._send_json(400, {"error": "workflow preflight request rejected"})
            return
        workflow_id, version = parts
        try:
            report = service_module.build_workflow_preflight(
                self.runtime_service.control_plane.get_workflow(workflow_id, version),
                input_value=payload.get("input"),
                input_present=input_present,
            )
            encoded = service_module.json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_PREFLIGHT_RESPONSE_BYTES:
                raise ValueError("workflow preflight exceeds response limit")
        except ValueError as error:
            message = str(error).lower()
            if "version not found" in message:
                self._send_json(404, {"error": "workflow version not found"})
            else:
                self._send_json(503, {"error": "workflow preflight unavailable"})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow preflight unavailable"})
            return
        self._send_json(200, report)

    def _handle_workflow_release_preflight(self):
        """Validate one candidate Workflow DSL document without storing it."""

        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
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
                or set(payload) != {"workflow"}
                or not isinstance(payload.get("workflow"), dict)
            ):
                raise ValueError(
                    "workflow release preflight request must contain one workflow object"
                )
            response = service_module.build_workflow_release_preflight(payload["workflow"])
            if response.get("schema_version") != service_module.WORKFLOW_RELEASE_PREFLIGHT_SCHEMA_VERSION:
                raise ValueError("workflow release preflight schema is invalid")
            encoded = service_module.json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_PREFLIGHT_BYTES:
                raise ValueError("workflow release preflight exceeds response limit")
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (
            UnicodeDecodeError,
            service_module.json.JSONDecodeError,
            TypeError,
            ValueError,
            OverflowError,
            RecursionError,
        ):
            self._send_json(400, {"error": "workflow release preflight rejected"})
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow release preflight unavailable"})
        else:
            self._send_json(200, response)

    def _handle_workflow_release_target_review(self):
        """Review one release candidate against the current immutable target."""

        readiness_status, _ = self.runtime_service.readiness()
        if readiness_status != 200:
            self._send_json(503, {"error": "service is not ready"})
            return
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
                or set(payload) != {"workflow"}
                or not isinstance(payload.get("workflow"), dict)
            ):
                raise ValueError(
                    "workflow release target review request must contain one workflow object"
                )
            workflow = payload["workflow"]
            release_preflight = service_module.build_workflow_release_preflight(workflow)
            identity = release_preflight["workflow"]
            existing = next(
                (
                    record
                    for record in self.runtime_service.control_plane.list_workflows()
                    if record.get("workflow_id") == identity["id"]
                    and record.get("version") == identity["version"]
                ),
                None,
            )
            response = service_module.build_workflow_release_target_review(workflow, existing)
            if (
                response.get("schema_version")
                != service_module.WORKFLOW_RELEASE_TARGET_REVIEW_SCHEMA_VERSION
            ):
                raise ValueError("workflow release target review schema is invalid")
            encoded = service_module.json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_PREFLIGHT_BYTES:
                raise ValueError("workflow release target review exceeds response limit")
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (
            UnicodeDecodeError,
            service_module.json.JSONDecodeError,
            TypeError,
            ValueError,
            OverflowError,
            RecursionError,
        ):
            self._send_json(400, {"error": "workflow release target review rejected"})
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow release target review unavailable"})
        else:
            self._send_json(200, response)

    def _handle_workflow_release(self):
        """Publish one validated immutable workflow through the service."""

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
                "workflow_release",
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
            "workflow_release",
        )
        try:
            body = service_module.read_request_body(self)
            payload = service_module.json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or set(payload) != {"workflow"}
                or not isinstance(payload.get("workflow"), dict)
            ):
                raise ValueError("workflow release request must contain one workflow object")
            record = self.runtime_service.control_plane.publish_workflow(payload["workflow"])
            response = {
                "schema_version": service_module.WORKFLOW_RELEASE_SCHEMA_VERSION,
                "workflow_id": str(record.get("workflow_id", "")),
                "version": str(record.get("version", "")),
                "status": str(record.get("status", "")),
                "checksum": str(record.get("checksum", "")),
            }
            encoded = service_module.json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_RELEASE_RESPONSE_BYTES:
                raise ValueError("workflow release response exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError, TypeError, ValueError, OverflowError, RecursionError) as error:
            if "immutable" in str(error).lower():
                self._send_json(409, {"error": "workflow version is immutable"})
            else:
                self._send_json(400, {"error": "workflow publication rejected"})
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow publication unavailable"})

    def _handle_workflow_promotion(self):
        """Move one stable alias through the authenticated service boundary."""

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
                "workflow_promotion",
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
            "workflow_promotion",
        )
        try:
            body = service_module.read_request_body(self)
            payload = service_module.json.loads(body.decode("utf-8"))
            fields = {
                "workflow_id",
                "version",
                "alias",
                "expected_current_version",
            }
            if (
                not isinstance(payload, dict)
                or set(payload) != fields
                or any(not isinstance(payload.get(field), str) for field in fields)
            ):
                raise ValueError("workflow promotion request is malformed")
            if not payload["expected_current_version"]:
                expected_current_version = ""
            else:
                expected_current_version = payload["expected_current_version"]
            record = self.runtime_service.control_plane.promote_workflow(
                payload["workflow_id"],
                payload["version"],
                alias=payload["alias"],
                expected_current_version=expected_current_version,
            )
            aliases = record.get("aliases", [])
            if not isinstance(aliases, list) or payload["alias"] not in aliases:
                raise ValueError("workflow promotion did not retain alias")
            response = {
                "schema_version": service_module.WORKFLOW_PROMOTION_SCHEMA_VERSION,
                "workflow_id": str(record.get("workflow_id", "")),
                "version": str(record.get("version", "")),
                "alias": payload["alias"],
                "status": "promoted",
                "checksum": str(record.get("checksum", "")),
            }
            encoded = service_module.json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_PROMOTION_RESPONSE_BYTES:
                raise ValueError("workflow promotion response exceeds response limit")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except ValueError as error:
            message = str(error).lower()
            if "precondition failed" in message:
                self._send_json(409, {"error": "workflow alias precondition failed"})
            elif "version not found" in message:
                self._send_json(404, {"error": "workflow version not found"})
            elif "not published" in message:
                self._send_json(409, {"error": "workflow version is not published"})
            else:
                self._send_json(400, {"error": "workflow promotion rejected"})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError, TypeError, OverflowError, RecursionError):
            self._send_json(400, {"error": "workflow promotion rejected"})
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow promotion unavailable"})

    def _handle_workflow_deprecation(self):
        """Deprecate one published workflow version through the service."""

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
                "workflow_deprecation",
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
            "workflow_deprecation",
        )
        try:
            body = service_module.read_request_body(self)
            payload = service_module.json.loads(body.decode("utf-8"))
            base_fields = {"workflow_id", "version"}
            cas_fields = base_fields | {"expected_checksum", "expected_aliases"}
            if (
                not isinstance(payload, dict)
                or set(payload) not in (base_fields, cas_fields)
                or any(
                    not isinstance(payload.get(field), str) or not payload.get(field)
                    for field in base_fields
                )
            ):
                raise ValueError("workflow deprecation request is malformed")
            expected_checksum = ""
            expected_aliases = None
            if set(payload) == cas_fields:
                expected_checksum = payload.get("expected_checksum")
                expected_aliases = payload.get("expected_aliases")
                if (
                    not isinstance(expected_checksum, str)
                    or len(expected_checksum) != 64
                    or any(
                        char not in "0123456789abcdef"
                        for char in expected_checksum
                    )
                    or not isinstance(expected_aliases, list)
                    or len(expected_aliases) > service_module.MAX_WORKFLOW_DEPRECATION_ALIASES
                    or any(
                        not isinstance(alias, str)
                        or not service_module._WORKFLOW_ALIAS_PATTERN.fullmatch(alias)
                        for alias in expected_aliases
                    )
                    or len(set(expected_aliases)) != len(expected_aliases)
                ):
                    raise ValueError("workflow deprecation request is malformed")
            record = self.runtime_service.control_plane.deprecate_workflow(
                payload["workflow_id"],
                payload["version"],
                expected_checksum=expected_checksum,
                expected_aliases=expected_aliases,
            )
            response = {
                "schema_version": service_module.WORKFLOW_DEPRECATION_SCHEMA_VERSION,
                "workflow_id": str(record.get("workflow_id", "")),
                "version": str(record.get("version", "")),
                "status": str(record.get("status", "")),
                "checksum": str(record.get("checksum", "")),
            }
            encoded = service_module.json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_DEPRECATION_RESPONSE_BYTES:
                raise ValueError("workflow deprecation response exceeds response limit")
            if response["status"] != "deprecated":
                raise ValueError("workflow deprecation did not persist status")
            self._send_json(200, response)
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
        except ValueError as error:
            message = str(error).lower()
            if "precondition failed" in message:
                self._send_json(409, {"error": "workflow deprecation conflict"})
            elif "version not found" in message:
                self._send_json(404, {"error": "workflow version not found"})
            else:
                self._send_json(400, {"error": "workflow deprecation rejected"})
        except (UnicodeDecodeError, service_module.json.JSONDecodeError, TypeError, OverflowError, RecursionError):
            self._send_json(400, {"error": "workflow deprecation rejected"})
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow deprecation unavailable"})

    def _handle_workflow_diff(self, parts):
        """Serve a bounded, value-free diff of two published versions."""

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
            if service_module._content_length(self) != 0:
                self._send_json(
                    400,
                    {"error": "workflow diff request must not include a body"},
                )
                return
        except service_module.WebhookError as error:
            self._send_json(error.status_code, {"error": str(error)})
            return
        workflow_id, from_version, to_version = parts
        try:
            payload = self.runtime_service.control_plane.diff_workflow_versions(
                workflow_id,
                from_version,
                to_version,
            )
            encoded = service_module.json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > service_module.MAX_WORKFLOW_DIFF_RESPONSE_BYTES:
                raise ValueError("workflow diff exceeds response limit")
        except ValueError as error:
            message = str(error).lower()
            if "version not found" in message:
                self._send_json(404, {"error": "workflow version not found"})
            elif "artifact unavailable" in message:
                self._send_json(503, {"error": "workflow diff unavailable"})
            else:
                self._send_json(503, {"error": "workflow diff unavailable"})
            return
        except (OSError, service_module.sqlite3.Error):
            self._send_json(503, {"error": "workflow diff unavailable"})
            return
        self._send_json(200, payload)
