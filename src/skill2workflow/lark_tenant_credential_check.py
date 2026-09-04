"""Explicit, value-free verification for self-hosted Feishu tenant credentials."""

from __future__ import annotations

from pathlib import Path

from .credentials import DirectoryCredentialProvider, LarkTenantAccessTokenCredentialProvider
from .service import load_service_config


LARK_TENANT_CREDENTIAL_CHECK_SCHEMA_VERSION = (
    "skill2workflow-lark-tenant-credential-check-0.1.0"
)


def check_lark_tenant_credential(config_path: Path):
    """Resolve one configured tenant token without printing or retaining it."""

    result = {
        "schema_version": LARK_TENANT_CREDENTIAL_CHECK_SCHEMA_VERSION,
        "status": "not_ready",
        "provider": "lark_tenant_access_token",
    }
    try:
        config = load_service_config(config_path)
    except (OSError, ValueError):
        result["reason"] = "invalid_config"
        return result
    if config.lark_tenant_access_token is None:
        result["reason"] = "not_configured"
        return result
    try:
        provider = LarkTenantAccessTokenCredentialProvider(
            DirectoryCredentialProvider(config.credential_dir),
            **config.lark_tenant_access_token,
        )
        provider.resolve(config.lark_tenant_access_token["handle"])
    except Exception:
        result["reason"] = "credential_unavailable"
        return result
    result["status"] = "ready"
    result["reason"] = "validated"
    return result
