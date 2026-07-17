"""Anchored private authorization sessions and finalization bundles."""

from __future__ import annotations

import json
import os
import stat
import fcntl
from dataclasses import dataclass
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


def _entry_fingerprint(item) -> tuple:
    return (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )


def _read_descriptor_bytes(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(descriptor, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return b"".join(chunks)


@dataclass
class AuthorizationEntrySnapshot:
    session: "AnchoredPrivateSession"
    name: str
    label: str
    descriptor: int
    fingerprint: tuple
    raw_content: bytes
    value: object
    closed: bool = False

    @classmethod
    def capture(
        cls,
        session: "AnchoredPrivateSession",
        name: str,
        label: str,
    ) -> "AuthorizationEntrySnapshot":
        descriptor = None
        try:
            try:
                descriptor = os.open(
                    name,
                    os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                    dir_fd=session.parent_fd,
                )
            except FileNotFoundError:
                raise
            except OSError as error:
                raise ValueError(
                    f"{label} must not be a symbolic link or non-regular file"
                ) from error
            opened = os.fstat(descriptor)
            _require_owner_only_regular(opened, label)
            named = os.stat(
                name,
                dir_fd=session.parent_fd,
                follow_symlinks=False,
            )
            _require_owner_only_regular(named, label)
            fingerprint = _entry_fingerprint(opened)
            if fingerprint != _entry_fingerprint(named):
                raise ValueError(f"{label} changed during authorization snapshot")
            raw_content = _read_descriptor_bytes(descriptor)
            value = json.loads(raw_content.decode("utf-8"))
            after = os.fstat(descriptor)
            named_after = os.stat(
                name,
                dir_fd=session.parent_fd,
                follow_symlinks=False,
            )
            if (
                fingerprint != _entry_fingerprint(after)
                or fingerprint != _entry_fingerprint(named_after)
                or raw_content != _read_descriptor_bytes(descriptor)
            ):
                raise ValueError(f"{label} changed during authorization snapshot")
            return cls(
                session=session,
                name=name,
                label=label,
                descriptor=descriptor,
                fingerprint=fingerprint,
                raw_content=raw_content,
                value=value,
            )
        except BaseException:
            _close_descriptors(descriptor)
            raise

    def validate(self) -> None:
        if self.closed or self.descriptor is None:
            raise ValueError(f"{self.label} authorization snapshot is closed")
        opened = os.fstat(self.descriptor)
        _require_owner_only_regular(opened, self.label)
        try:
            named = os.stat(
                self.name,
                dir_fd=self.session.parent_fd,
                follow_symlinks=False,
            )
        except (FileNotFoundError, OSError) as error:
            raise ValueError(f"{self.label} changed after authorization snapshot") from error
        _require_owner_only_regular(named, self.label)
        if (
            self.fingerprint != _entry_fingerprint(opened)
            or self.fingerprint != _entry_fingerprint(named)
            or self.raw_content != _read_descriptor_bytes(self.descriptor)
        ):
            raise ValueError(f"{self.label} changed after authorization snapshot")

    def close(self) -> None:
        if self.closed:
            return
        descriptor = self.descriptor
        try:
            _close_descriptors(descriptor)
        except BaseException:
            try:
                os.fstat(descriptor)
            except OSError:
                self.descriptor = None
                self.closed = True
            raise
        self.descriptor = None
        self.closed = True

    def isolate_cleanup_failure(self) -> None:
        descriptor = self.descriptor
        self.descriptor = None
        self.closed = True
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


class AuthorizationBundleSnapshot:
    """Retain one immutable decision/marker authorization view."""

    def __init__(self, session: "AnchoredPrivateSession"):
        self.session = session
        self.decision_entry = None
        self.marker_entry = None
        self.closed = False
        try:
            session.check_identity()
            self.decision_entry = AuthorizationEntrySnapshot.capture(
                session,
                "decision.json",
                "private decision",
            )
            self.marker_entry = AuthorizationEntrySnapshot.capture(
                session,
                "finalization.json",
                "private finalization marker",
            )
            self.validate()
        except BaseException:
            self.close()
            raise

    @property
    def decision(self):
        return self.decision_entry.value

    @property
    def marker(self):
        return self.marker_entry.value

    def validate(self) -> None:
        if self.closed:
            raise ValueError("private authorization bundle snapshot is closed")
        self.session.check_identity()
        self.decision_entry.validate()
        self.marker_entry.validate()
        self.session.check_identity()

    def close(self) -> None:
        if self.closed:
            return
        first_error = None
        for entry in (self.marker_entry, self.decision_entry):
            if entry is None:
                continue
            try:
                entry.close()
            except BaseException as error:
                if first_error is None:
                    first_error = error
        self.closed = all(
            entry is None or entry.closed
            for entry in (self.marker_entry, self.decision_entry)
        )
        if first_error is not None:
            raise first_error

    def isolate_cleanup_failure(self) -> None:
        for entry in (self.marker_entry, self.decision_entry):
            if entry is not None:
                entry.isolate_cleanup_failure()
        self.closed = True


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
        flags = os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW
        created = False
        descriptor = None
        locked = False
        completed = False
        try:
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
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
            observed = os.stat(
                self.LOCK_NAME,
                dir_fd=self.parent_fd,
                follow_symlinks=False,
            )
            _require_owner_only_regular(observed, "private authorization lock")
            if not _same_entry(item, observed):
                raise ValueError("private authorization lock changed during open")
            os.fsync(self.parent_fd)
            completed = True
            return descriptor
        except BlockingIOError as error:
            raise ValueError("private authorization session is busy") from error
        except BaseException:
            raise
        finally:
            if descriptor is not None and not completed:
                if locked:
                    try:
                        fcntl.flock(descriptor, fcntl.LOCK_UN)
                    except OSError:
                        pass
                try:
                    os.close(descriptor)
                except OSError:
                    pass

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
        if self.lock_fd is None:
            raise ValueError("private authorization lock changed")
        opened_lock = os.fstat(self.lock_fd)
        _require_owner_only_regular(opened_lock, "private authorization lock")
        try:
            named_lock = os.stat(
                self.LOCK_NAME,
                dir_fd=self.parent_fd,
                follow_symlinks=False,
            )
        except (FileNotFoundError, OSError) as error:
            raise ValueError("private authorization lock changed") from error
        _require_owner_only_regular(named_lock, "private authorization lock")
        if not _same_entry(opened_lock, named_lock):
            raise ValueError("private authorization lock changed")

    def authorization_bundle_snapshot(self) -> AuthorizationBundleSnapshot:
        return AuthorizationBundleSnapshot(self)

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
        if self.lock_fd is not None:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            except BaseException as error:
                first_error = error
        for attribute in ("lock_fd", "parent_fd", "root_fd"):
            descriptor = getattr(self, attribute)
            if descriptor is None:
                continue
            try:
                _close_descriptors(descriptor)
            except BaseException as error:
                try:
                    os.fstat(descriptor)
                except OSError:
                    setattr(self, attribute, None)
                if first_error is None:
                    first_error = error
            else:
                setattr(self, attribute, None)
        self.closed = all(
            getattr(self, attribute) is None
            for attribute in ("lock_fd", "parent_fd", "root_fd")
        )
        if first_error is not None:
            raise first_error

    def isolate_cleanup_failure(self) -> None:
        if self.lock_fd is not None:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
        for attribute in ("lock_fd", "parent_fd", "root_fd"):
            descriptor = getattr(self, attribute)
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            setattr(self, attribute, None)
        self.closed = True

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

    def publish_marker(self, marker: object) -> AuthorizationBundleSnapshot:
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
        return self.session.authorization_bundle_snapshot()

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
        if self.transaction_fd is not None:
            descriptor = self.transaction_fd
            try:
                _close_descriptors(descriptor)
            except BaseException as error:
                try:
                    os.fstat(descriptor)
                except OSError:
                    self.transaction_fd = None
                first_error = error
            else:
                self.transaction_fd = None
        if self.transaction_fd is None and self.transaction_name:
            try:
                _remove_tree_at(self.session.parent_fd, self.transaction_name)
                os.fsync(self.session.parent_fd)
                self.transaction_name = ""
            except BaseException as error:
                if first_error is None:
                    first_error = error
        self.closed = self.transaction_fd is None and not self.transaction_name
        if first_error is not None:
            raise first_error

    def isolate_cleanup_failure(self) -> None:
        if self.transaction_fd is not None:
            try:
                os.close(self.transaction_fd)
            except OSError:
                pass
        self.transaction_fd = None
        self.closed = True
