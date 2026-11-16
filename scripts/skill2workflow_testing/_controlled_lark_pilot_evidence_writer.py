"""Checkout-only evidence packs built on the runtime private JSON boundary."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Dict

from skill2workflow.private_json import (
    _remove_tree_at as _remove_tree_at,
    _allocate_transaction_directory as _allocate_transaction_directory,
    _require_dir_fd_support as _require_dir_fd_support,
    _directory_flags as _directory_flags,
    _canonicalize_root_alias as _canonicalize_root_alias,
    _close_descriptors as _close_descriptors,
    _open_child_directory as _open_child_directory,
    _open_relative_directory as _open_relative_directory,
    _read_json_at as _read_json_at,
    read_json_anchored as read_json_anchored,
    _require_declared_directory_identity as _require_declared_directory_identity,
    _private_target_stat as _private_target_stat,
    _same_entry as _same_entry,
    _open_private_parent as _open_private_parent,
    ensure_private_directory_anchored as ensure_private_directory_anchored,
    require_private_json_target as require_private_json_target,
    invalidate_private_json_anchored as invalidate_private_json_anchored,
    _write_private_json_at as _write_private_json_at,
    write_private_json_anchored as write_private_json_anchored,
)
from ._controlled_lark_pilot_pack_transaction import EvidencePackTransaction, PackTransactionIO


def _write_json_atomic(parent_fd: int, name: str, value: object) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = None
    temporary = ""
    try:
        for _attempt in range(16):
            temporary = f".{name}.{secrets.token_hex(8)}.tmp"
            try:
                descriptor = os.open(
                    temporary,
                    flags,
                    0o600,
                    dir_fd=parent_fd,
                )
                break
            except FileExistsError:
                continue
        if descriptor is None:
            raise FileExistsError("could not allocate an evidence temporary file")
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(
            temporary,
            name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        temporary = ""
        os.fsync(parent_fd)
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
        finally:
            if temporary:
                try:
                    os.unlink(temporary, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass






def _pack_io() -> PackTransactionIO:
    return PackTransactionIO(
        require_dir_fd_support=_require_dir_fd_support,
        directory_flags=_directory_flags,
        close_descriptors=_close_descriptors,
        open_relative_directory=_open_relative_directory,
        require_declared_directory_identity=_require_declared_directory_identity,
        same_entry=_same_entry,
        write_json_atomic=_write_json_atomic,
        remove_tree_at=_remove_tree_at,
        allocate_transaction_directory=_allocate_transaction_directory,
    )


def prepare_evidence_pack(
    output_dir: Path,
    pack: Dict[str, object],
) -> EvidencePackTransaction:
    return EvidencePackTransaction(_pack_io(), output_dir, pack)


def finish_durable_resources(*resources) -> None:
    """Best-effort cleanup after the caller's durable commit point."""
    pending = list(resources)
    for _attempt in range(2):
        retry = []
        for resource, method_name in pending:
            try:
                getattr(resource, method_name)()
            except Exception:
                retry.append((resource, method_name))
        pending = retry
        if not pending:
            return
    for resource, _method_name in pending:
        isolate = getattr(resource, "isolate_cleanup_failure", None)
        if isolate is None:
            continue
        try:
            isolate()
        except Exception:
            pass


def write_evidence_pack(output_dir: Path, pack: Dict[str, object]) -> Dict[str, object]:
    transaction = prepare_evidence_pack(output_dir, pack)
    try:
        transaction.commit()
    except BaseException:
        transaction.abort()
        raise
    result = {
        "status": "written",
        "file_count": transaction.file_count,
        "output_dir": str(transaction.output),
    }
    finish_durable_resources((transaction, "finish"))
    return result
