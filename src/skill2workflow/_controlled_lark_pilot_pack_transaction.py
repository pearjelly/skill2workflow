"""Whole-directory evidence pack staging, commit, and rollback."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Set


@dataclass(frozen=True)
class PackTransactionIO:
    require_dir_fd_support: Callable
    directory_flags: Callable
    close_descriptors: Callable
    open_relative_directory: Callable
    require_declared_directory_identity: Callable
    same_entry: Callable
    write_json_atomic: Callable
    remove_tree_at: Callable
    allocate_transaction_directory: Callable


def _remove_stale_json_files(
    io: PackTransactionIO,
    directory_fd: int,
    expected: Set[str],
    prefix: tuple = (),
) -> None:
    for name in os.listdir(directory_fd):
        item = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        relative = "/".join(prefix + (name,))
        if stat.S_ISLNK(item.st_mode):
            raise ValueError("evidence output descendants must not be symbolic links")
        if stat.S_ISDIR(item.st_mode):
            child = _open_directory_at(io, directory_fd, name)
            try:
                _remove_stale_json_files(
                    io,
                    child,
                    expected,
                    prefix + (name,),
                )
            finally:
                os.close(child)
            continue
        if not stat.S_ISREG(item.st_mode):
            raise ValueError("evidence output descendants must be regular files")
        if name.endswith(".json") and relative not in expected:
            os.unlink(name, dir_fd=directory_fd)


def _pack_files(pack: Dict[str, object]) -> Dict[tuple, object]:
    files = {
        ((), "pilot-charter.json"): pack["charter"],
        ((), "evidence-index.json"): pack["index"],
    }
    for sequence, run in enumerate(pack["runs"], start=1):
        files[(("runs",), f"{sequence:03d}.json")] = run
    for name in ("rejection", "failure", "rollback"):
        exercise = pack["exercises"][name]
        if exercise is not None:
            files[(("exercises",), f"{name}.json")] = exercise
    if pack["verification"] is not None:
        files[((), "verification.json")] = pack["verification"]
    if pack["decision"] is not None:
        files[((), "decision.json")] = pack["decision"]
    return files


def _open_output_parent(io: PackTransactionIO, output_dir: Path) -> tuple:
    io.require_dir_fd_support()
    output = Path(os.path.abspath(os.fspath(output_dir)))
    if output == Path(output.anchor) or not output.name:
        raise ValueError("evidence output must not be a filesystem root")
    root_fd = os.open(output.anchor, io.directory_flags())
    parent_fd = None
    try:
        parent_fd = io.open_relative_directory(
            root_fd,
            output.parts[1:-1],
            create=True,
        )
        return output, root_fd, parent_fd
    except BaseException:
        io.close_descriptors(parent_fd, root_fd)
        raise


def _output_target_stat(parent_fd: int, name: str):
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(item.st_mode):
        raise ValueError("evidence output must not be a symbolic link")
    if not stat.S_ISDIR(item.st_mode):
        raise ValueError("evidence output must be a directory")
    return item


def _open_directory_at(
    io: PackTransactionIO,
    parent_fd: int,
    name: str,
) -> int:
    try:
        return os.open(name, io.directory_flags(), dir_fd=parent_fd)
    except OSError as error:
        raise ValueError("evidence output must remain a directory") from error


def _clone_directory(
    io: PackTransactionIO,
    source_fd: int,
    destination_fd: int,
) -> None:
    for name in os.listdir(source_fd):
        source_stat = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
        if stat.S_ISLNK(source_stat.st_mode):
            raise ValueError("evidence output descendants must not be symbolic links")
        if stat.S_ISDIR(source_stat.st_mode):
            os.mkdir(name, 0o700, dir_fd=destination_fd)
            source_child = _open_directory_at(io, source_fd, name)
            destination_child = _open_directory_at(io, destination_fd, name)
            try:
                _clone_directory(io, source_child, destination_child)
                os.fsync(destination_child)
            finally:
                io.close_descriptors(destination_child, source_child)
            continue
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError("evidence output descendants must be regular files")
        os.link(
            name,
            name,
            src_dir_fd=source_fd,
            dst_dir_fd=destination_fd,
            follow_symlinks=False,
        )
        cloned_stat = os.stat(name, dir_fd=destination_fd, follow_symlinks=False)
        if not stat.S_ISREG(cloned_stat.st_mode) or not io.same_entry(
            source_stat,
            cloned_stat,
        ):
            raise ValueError("evidence output descendant changed during staging")


class EvidencePackTransaction:
    """Prepare and atomically exchange one complete evidence directory."""

    def __init__(
        self,
        io: PackTransactionIO,
        output_dir: Path,
        pack: Dict[str, object],
    ):
        self.io = io
        self.output, self.root_fd, self.parent_fd = _open_output_parent(
            io,
            output_dir,
        )
        self.output_fd = None
        self.transaction_fd = None
        self.stage_fd = None
        self.reservation_fd = None
        self.transaction_name = ""
        self.initial = None
        self.published = None
        self.committed = False
        self.closed = False
        self.file_count = 0
        try:
            self.initial = _output_target_stat(self.parent_fd, self.output.name)
            if self.initial is not None:
                self.output_fd = _open_directory_at(
                    io,
                    self.parent_fd,
                    self.output.name,
                )
                if not io.same_entry(self.initial, os.fstat(self.output_fd)):
                    raise ValueError("evidence output changed during transaction setup")
            self.transaction_name, self.transaction_fd = (
                io.allocate_transaction_directory(
                    self.parent_fd,
                    self.output.name,
                )
            )
            os.mkdir("stage", 0o700, dir_fd=self.transaction_fd)
            self.stage_fd = _open_directory_at(io, self.transaction_fd, "stage")
            if self.output_fd is not None:
                _clone_directory(io, self.output_fd, self.stage_fd)
            files = _pack_files(pack)
            expected = {
                "/".join(components + (name,))
                for components, name in files
            }
            for (components, name), item in files.items():
                parent_fd = io.open_relative_directory(
                    self.stage_fd,
                    components,
                    create=True,
                )
                try:
                    io.write_json_atomic(parent_fd, name, item)
                finally:
                    os.close(parent_fd)
            _remove_stale_json_files(io, self.stage_fd, expected)
            os.fsync(self.stage_fd)
            self.file_count = len(files)
            self._require_initial_identity()
        except BaseException:
            self._cleanup_uncommitted()
            raise

    def _require_parent_identity(self) -> None:
        self.io.require_declared_directory_identity(
            self.root_fd,
            self.output.parent,
            self.parent_fd,
            "output parent",
        )

    def _require_initial_identity(self) -> None:
        self._require_parent_identity()
        current = _output_target_stat(self.parent_fd, self.output.name)
        if not self.io.same_entry(self.initial, current):
            raise ValueError("declared output path changed during transaction")
        if self.output_fd is not None and not self.io.same_entry(
            self.initial,
            os.fstat(self.output_fd),
        ):
            raise ValueError("declared output path changed during transaction")

    def _require_published_identity(self, *, require_declared_parent: bool = True) -> None:
        if require_declared_parent:
            self._require_parent_identity()
        published = _open_directory_at(self.io, self.parent_fd, self.output.name)
        try:
            expected = (
                self.published
                if self.published is not None
                else os.fstat(self.stage_fd)
            )
            observed = os.fstat(published)
            if not self.io.same_entry(expected, observed):
                raise ValueError("published evidence output identity is invalid")
            if self.published is None:
                self.published = observed
        finally:
            os.close(published)

    def commit(self) -> None:
        if self.closed or self.committed:
            raise ValueError("evidence transaction cannot be committed")
        self._require_initial_identity()
        moved_old = False
        reserved = False
        published = False
        try:
            if self.initial is not None:
                os.rename(
                    self.output.name,
                    "backup",
                    src_dir_fd=self.parent_fd,
                    dst_dir_fd=self.transaction_fd,
                )
                moved_old = True
            os.mkdir(self.output.name, 0o700, dir_fd=self.parent_fd)
            reserved = True
            self.reservation_fd = _open_directory_at(
                self.io,
                self.parent_fd,
                self.output.name,
            )
            reservation = _output_target_stat(
                self.parent_fd,
                self.output.name,
            )
            if not self.io.same_entry(
                reservation,
                os.fstat(self.reservation_fd),
            ):
                raise ValueError("evidence output reservation changed before publish")
            os.replace(
                "stage",
                self.output.name,
                src_dir_fd=self.transaction_fd,
                dst_dir_fd=self.parent_fd,
            )
            published = True
            os.fsync(self.parent_fd)
            self.committed = True
            self._require_published_identity()
        except BaseException as error:
            try:
                if published:
                    self.committed = True
                    self.rollback()
                elif moved_old:
                    os.rename(
                        "backup",
                        self.output.name,
                        src_dir_fd=self.transaction_fd,
                        dst_dir_fd=self.parent_fd,
                    )
                    os.fsync(self.parent_fd)
                elif reserved:
                    current = _output_target_stat(
                        self.parent_fd,
                        self.output.name,
                    )
                    if (
                        current is not None
                        and self.reservation_fd is not None
                        and self.io.same_entry(
                            current,
                            os.fstat(self.reservation_fd),
                        )
                    ):
                        os.rmdir(self.output.name, dir_fd=self.parent_fd)
                        os.fsync(self.parent_fd)
            except BaseException as rollback_error:
                raise RuntimeError(
                    "evidence transaction commit rollback failed"
                ) from rollback_error
            raise error

    def rollback(self) -> None:
        if self.closed or not self.committed:
            return
        self._require_published_identity(require_declared_parent=False)
        os.rename(
            self.output.name,
            "failed",
            src_dir_fd=self.parent_fd,
            dst_dir_fd=self.transaction_fd,
        )
        if self.initial is not None:
            os.rename(
                "backup",
                self.output.name,
                src_dir_fd=self.transaction_fd,
                dst_dir_fd=self.parent_fd,
            )
        os.fsync(self.parent_fd)
        self.committed = False
        self._require_parent_identity()

    def finish(self) -> None:
        if self.closed:
            return
        self.validate_durable_commit()
        self._cleanup_uncommitted()

    def validate_durable_commit(self) -> None:
        if self.closed or not self.committed:
            raise ValueError("evidence transaction is not durably committed")
        self._require_published_identity()

    def abort(self) -> None:
        if self.closed:
            return
        rollback_error = None
        try:
            if self.committed:
                self.rollback()
        except BaseException as error:
            rollback_error = error
        try:
            self._cleanup_uncommitted()
        except BaseException as error:
            if rollback_error is None:
                rollback_error = error
        if rollback_error is not None:
            raise RuntimeError("evidence transaction rollback failed") from rollback_error

    def _cleanup_uncommitted(self) -> None:
        if self.closed:
            return
        first_error = None
        for attribute in (
            "reservation_fd",
            "stage_fd",
            "output_fd",
            "transaction_fd",
        ):
            try:
                self._close_descriptor_attribute(attribute)
            except BaseException as error:
                if first_error is None:
                    first_error = error
        transaction_descriptors_closed = all(
            getattr(self, attribute) is None
            for attribute in (
                "reservation_fd",
                "stage_fd",
                "output_fd",
                "transaction_fd",
            )
        )
        if transaction_descriptors_closed and self.transaction_name:
            try:
                self.io.remove_tree_at(self.parent_fd, self.transaction_name)
                os.fsync(self.parent_fd)
                self.transaction_name = ""
            except BaseException as error:
                if first_error is None:
                    first_error = error
        if not self.transaction_name:
            for attribute in ("parent_fd", "root_fd"):
                try:
                    self._close_descriptor_attribute(attribute)
                except BaseException as error:
                    if first_error is None:
                        first_error = error
            self.closed = self.parent_fd is None and self.root_fd is None
        if first_error is not None:
            raise first_error

    def _close_descriptor_attribute(self, attribute: str) -> None:
        descriptor = getattr(self, attribute)
        if descriptor is None:
            return
        try:
            self.io.close_descriptors(descriptor)
        except BaseException:
            try:
                os.fstat(descriptor)
            except OSError:
                setattr(self, attribute, None)
            raise
        setattr(self, attribute, None)

    def isolate_cleanup_failure(self) -> None:
        """Close descriptors while preserving an owner-only hidden residual."""
        if self.closed:
            return
        for attribute in (
            "reservation_fd",
            "stage_fd",
            "output_fd",
            "transaction_fd",
            "parent_fd",
            "root_fd",
        ):
            descriptor = getattr(self, attribute)
            if descriptor is None:
                continue
            for _attempt in range(2):
                try:
                    os.close(descriptor)
                    break
                except OSError:
                    try:
                        os.fstat(descriptor)
                    except OSError:
                        break
            setattr(self, attribute, None)
        self.closed = True
