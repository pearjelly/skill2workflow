"""Anchored private authorization sessions and finalization bundles."""

from __future__ import annotations

import os
import stat
import fcntl
from pathlib import Path

from ._controlled_lark_pilot_evidence_writer import (
    _allocate_transaction_directory,
    _close_descriptors,
    _open_private_parent,
    _open_relative_directory,
    _private_target_stat,
    _read_json_at,
    _remove_tree_at,
    _require_declared_directory_identity,
    _same_entry,
    _write_private_json_at,
)


def _require_owner_only_regular(item, label: str) -> None:
    if item is None or not stat.S_ISREG(item.st_mode):
        raise ValueError(f"{label} must be a regular file")
    if os.name == "posix" and item.st_mode & 0o077:
        raise ValueError(f"{label} must use owner-only permissions")


def _remove_authorization_target(parent_fd: int, name: str) -> None:
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode):
        os.rmdir(name, dir_fd=parent_fd)
    else:
        os.unlink(name, dir_fd=parent_fd)


def _invalidate_declared_marker(
    private_dir: Path,
    original_parent_fd: int,
) -> None:
    try:
        _absolute, root_fd, parent_fd = _open_private_parent(
            Path(private_dir) / ".rollback-placeholder",
            create=False,
        )
    except (FileNotFoundError, OSError, ValueError):
        return
    try:
        if not _same_entry(os.fstat(original_parent_fd), os.fstat(parent_fd)):
            _remove_authorization_target(parent_fd, "finalization.json")
            os.fsync(parent_fd)
        if _private_target_stat(parent_fd, "finalization.json") is not None:
            raise RuntimeError("declared private path retained finalization authorization")
    finally:
        _close_descriptors(parent_fd, root_fd)


class AnchoredPrivateSession:
    """Hold one owner-only private directory identity and exclusive auth lock."""

    LOCK_NAME = ".pilot-authorization.lock"

    def __init__(self, private_dir: Path):
        placeholder = Path(private_dir) / ".session-placeholder"
        absolute, self.root_fd, self.parent_fd = _open_private_parent(
            placeholder,
            create=False,
        )
        self.private_dir = absolute.parent
        self.lock_fd = None
        self.closed = False
        try:
            self.lock_fd = self._open_lock()
            self.check_identity()
        except BaseException:
            _close_descriptors(self.lock_fd, self.parent_fd, self.root_fd)
            self.lock_fd = None
            self.parent_fd = None
            self.root_fd = None
            self.closed = True
            raise

    def _open_lock(self) -> int:
        flags = os.O_RDWR | os.O_NOFOLLOW
        created = False
        try:
            descriptor = os.open(
                self.LOCK_NAME,
                flags | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=self.parent_fd,
            )
            created = True
        except FileExistsError:
            try:
                descriptor = os.open(
                    self.LOCK_NAME,
                    flags,
                    dir_fd=self.parent_fd,
                )
            except OSError as error:
                raise ValueError("private authorization lock is invalid") from error
        item = os.fstat(descriptor)
        if created:
            os.fchmod(descriptor, 0o600)
            item = os.fstat(descriptor)
        _require_owner_only_regular(item, "private authorization lock")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            os.close(descriptor)
            raise ValueError("private authorization session is busy") from error
        observed = os.stat(
            self.LOCK_NAME,
            dir_fd=self.parent_fd,
            follow_symlinks=False,
        )
        if not _same_entry(item, observed):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
            raise ValueError("private authorization lock changed during open")
        os.fsync(self.parent_fd)
        return descriptor

    def check_identity(self) -> None:
        if self.closed:
            raise ValueError("private authorization session is closed")
        _require_declared_directory_identity(
            self.root_fd,
            self.private_dir,
            self.parent_fd,
            "private authorization",
        )
        parent_mode = os.fstat(self.parent_fd).st_mode
        if parent_mode & 0o077:
            raise ValueError("private authorization parent must use owner-only permissions")

    def read_json(self, relative_path: Path, *, required: bool = True):
        if self.closed:
            raise ValueError("private authorization session is closed")
        relative = Path(relative_path)
        if relative.is_absolute() or not relative.name or ".." in relative.parts:
            raise ValueError("private authorization path must be relative")
        try:
            parent_fd = _open_relative_directory(
                self.parent_fd,
                relative.parts[:-1],
                create=False,
            )
        except FileNotFoundError:
            if required:
                raise
            return None
        try:
            try:
                return _read_json_at(parent_fd, relative.name, owner_only=True)
            except FileNotFoundError:
                if required:
                    raise
                return None
        finally:
            os.close(parent_fd)

    def close(self) -> None:
        if self.closed:
            return
        first_error = None
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
        except BaseException as error:
            first_error = error
        try:
            _close_descriptors(self.lock_fd, self.parent_fd, self.root_fd)
        except BaseException as error:
            if first_error is None:
                first_error = error
        self.lock_fd = None
        self.parent_fd = None
        self.root_fd = None
        self.closed = True
        if first_error is not None:
            raise first_error

    def __enter__(self):
        return self

    def __exit__(self, _error_type, _error, _traceback):
        self.close()


def open_private_session(private_dir: Path) -> AnchoredPrivateSession:
    return AnchoredPrivateSession(private_dir)


class PrivateFinalizationBundle:
    """Transactionally publish decision then marker within one private session."""

    def __init__(self, session: AnchoredPrivateSession):
        self.session = session
        self.transaction_name = ""
        self.transaction_fd = None
        self.initial_decision = None
        self.has_backup = False
        self.decision_published = False
        self.marker_published = False
        self.closed = False
        try:
            session.check_identity()
            if _private_target_stat(session.parent_fd, "finalization.json") is not None:
                raise ValueError("controlled pilot is already finalized")
            self.initial_decision = _private_target_stat(
                session.parent_fd,
                "decision.json",
            )
            if self.initial_decision is not None:
                _require_owner_only_regular(
                    self.initial_decision,
                    "private decision",
                )
            self.transaction_name, self.transaction_fd = (
                _allocate_transaction_directory(
                    session.parent_fd,
                    "finalization",
                )
            )
            if self.initial_decision is not None:
                os.link(
                    "decision.json",
                    "decision-backup",
                    src_dir_fd=session.parent_fd,
                    dst_dir_fd=self.transaction_fd,
                    follow_symlinks=False,
                )
                backup = os.stat(
                    "decision-backup",
                    dir_fd=self.transaction_fd,
                    follow_symlinks=False,
                )
                if not _same_entry(self.initial_decision, backup):
                    raise ValueError("private decision changed during backup")
                self.has_backup = True
            session.check_identity()
        except BaseException:
            self._cleanup_transaction()
            raise

    def publish_decision(self, decision: object) -> None:
        if self.closed or self.decision_published:
            raise ValueError("private decision cannot be published")
        _write_private_json_at(
            self.session.parent_fd,
            "decision.json",
            decision,
        )
        self.decision_published = True
        self.session.check_identity()

    def publish_marker(self, marker: object) -> tuple:
        if self.closed or not self.decision_published or self.marker_published:
            raise ValueError("private finalization marker cannot be published")
        self.session.check_identity()
        _write_private_json_at(
            self.session.parent_fd,
            "finalization.json",
            marker,
            require_missing=True,
        )
        self.marker_published = True
        self.session.check_identity()
        observed_decision = self.session.read_json(Path("decision.json"))
        observed_marker = self.session.read_json(Path("finalization.json"))
        self.session.check_identity()
        return observed_decision, observed_marker

    def rollback(self) -> None:
        if self.closed:
            return
        first_error = None
        try:
            _remove_authorization_target(
                self.session.parent_fd,
                "finalization.json",
            )
            if self.has_backup:
                os.replace(
                    "decision-backup",
                    "decision.json",
                    src_dir_fd=self.transaction_fd,
                    dst_dir_fd=self.session.parent_fd,
                )
                self.has_backup = False
            else:
                _remove_authorization_target(
                    self.session.parent_fd,
                    "decision.json",
                )
            os.fsync(self.session.parent_fd)
        except BaseException as error:
            first_error = error
        try:
            _invalidate_declared_marker(
                self.session.private_dir,
                self.session.parent_fd,
            )
        except BaseException as error:
            if first_error is None:
                first_error = error
        try:
            self._cleanup_transaction()
        except BaseException as error:
            if first_error is None:
                first_error = error
        if first_error is not None:
            raise RuntimeError("private finalization rollback failed") from first_error

    def finish(self) -> None:
        if self.closed:
            return
        if not self.marker_published:
            raise ValueError("private finalization bundle is incomplete")
        self.session.check_identity()
        self._cleanup_transaction()

    def _cleanup_transaction(self) -> None:
        if self.closed:
            return
        first_error = None
        try:
            _close_descriptors(self.transaction_fd)
        except BaseException as error:
            first_error = error
        self.transaction_fd = None
        try:
            if self.transaction_name:
                _remove_tree_at(self.session.parent_fd, self.transaction_name)
                os.fsync(self.session.parent_fd)
        except BaseException as error:
            if first_error is None:
                first_error = error
        self.closed = True
        if first_error is not None:
            raise first_error
