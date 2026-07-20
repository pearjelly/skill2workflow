"""Secure low-level I/O and stable evidence-writer facade."""

from __future__ import annotations

import inspect
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Dict

from ._controlled_lark_pilot_pack_transaction import (
    EvidencePackTransaction,
    PackTransactionIO,
)


def _replace_supports_dir_fd() -> bool:
    try:
        parameters = inspect.signature(os.replace).parameters
    except (TypeError, ValueError):
        return False
    return "src_dir_fd" in parameters and "dst_dir_fd" in parameters


_DIR_FD_SUPPORTED = bool(
    os.name == "posix"
    and hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_NONBLOCK")
    and all(
        function in os.supports_dir_fd
        for function in (
            os.open,
            os.mkdir,
            os.stat,
            os.unlink,
            os.link,
            os.rename,
            os.rmdir,
        )
    )
    and all(
        function in os.supports_follow_symlinks
        for function in (os.stat, os.link)
    )
    and os.listdir in os.supports_fd
    and _replace_supports_dir_fd()
)


def _require_dir_fd_support() -> None:
    if not _DIR_FD_SUPPORTED:
        raise ValueError("secure directory-fd evidence writes are not supported")


def _directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _canonicalize_root_alias(path: Path) -> Path:
    """Resolve only a root-owned top-level alias such as macOS /var."""
    if len(path.parts) < 2:
        return path
    top_level = Path(path.anchor) / path.parts[1]
    try:
        top_level_item = os.stat(top_level, follow_symlinks=False)
    except OSError:
        return path
    if not stat.S_ISLNK(top_level_item.st_mode):
        return path
    if hasattr(top_level_item, "st_uid") and top_level_item.st_uid != 0:
        return path
    resolved = top_level.resolve(strict=True)
    return resolved.joinpath(*path.parts[2:])


def _close_descriptors(*descriptors) -> None:
    first_error = None
    for descriptor in descriptors:
        if descriptor is None:
            continue
        try:
            os.close(descriptor)
        except BaseException as error:
            if first_error is None:
                first_error = error
    if first_error is not None:
        raise first_error


def _open_child_directory(parent_fd: int, name: str, create: bool) -> int:
    try:
        return os.open(name, _directory_flags(), dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
        try:
            return os.open(name, _directory_flags(), dir_fd=parent_fd)
        except OSError as error:
            raise ValueError(
                "evidence output component must not be a symbolic link or non-directory"
            ) from error
    except OSError as error:
        raise ValueError(
            "evidence output component must not be a symbolic link or non-directory"
        ) from error


def _open_relative_directory(root_fd: int, components: tuple, create: bool) -> int:
    descriptor = os.dup(root_fd)
    try:
        for component in components:
            child = _open_child_directory(descriptor, component, create=create)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_json_at(parent_fd: int, name: str, *, owner_only: bool = False):
    file_descriptor = None
    try:
        try:
            file_descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
        except FileNotFoundError:
            raise
        except OSError as error:
            raise ValueError(
                "anchored JSON file must not be a symbolic link or non-regular file"
            ) from error
        item = os.fstat(file_descriptor)
        if not stat.S_ISREG(item.st_mode):
            raise ValueError("anchored JSON file must be a regular file")
        if owner_only and os.name == "posix" and item.st_mode & 0o077:
            raise ValueError("private authorization JSON must use owner-only permissions")
        handle = os.fdopen(file_descriptor, "r", encoding="utf-8")
        file_descriptor = None
        with handle:
            return json.load(handle)
    finally:
        _close_descriptors(file_descriptor)


def read_json_anchored(path: Path, *, owner_only: bool = False):
    _require_dir_fd_support()
    absolute = _canonicalize_root_alias(
        Path(os.path.abspath(os.fspath(path)))
    )
    if absolute == Path(absolute.anchor):
        raise ValueError("anchored JSON path must not be a filesystem root")
    root_fd = os.open(absolute.anchor, _directory_flags())
    parent_fd = None
    try:
        parent_fd = _open_relative_directory(
            root_fd,
            absolute.parts[1:-1],
            create=False,
        )
        return _read_json_at(
            parent_fd,
            absolute.name,
            owner_only=owner_only,
        )
    finally:
        _close_descriptors(parent_fd, root_fd)


def _require_declared_directory_identity(
    root_fd: int,
    output: Path,
    anchored_output_fd: int,
    label: str,
) -> None:
    observed = None
    try:
        try:
            observed = _open_relative_directory(
                root_fd,
                output.parts[1:],
                create=False,
            )
        except (FileNotFoundError, OSError, ValueError) as error:
            raise ValueError(f"declared {label} path changed during write") from error
        expected_stat = os.fstat(anchored_output_fd)
        observed_stat = os.fstat(observed)
        if (expected_stat.st_dev, expected_stat.st_ino) != (
            observed_stat.st_dev,
            observed_stat.st_ino,
        ):
            raise ValueError(f"declared {label} path changed during write")
    finally:
        if observed is not None:
            os.close(observed)


def _private_target_stat(parent_fd: int, name: str):
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(item.st_mode):
        raise ValueError("private JSON target must not be a symbolic link")
    if not stat.S_ISREG(item.st_mode):
        raise ValueError("private JSON target must be a regular file")
    return item


def _same_entry(first, second) -> bool:
    if first is None or second is None:
        return first is second
    return (first.st_dev, first.st_ino, first.st_mode) == (
        second.st_dev,
        second.st_ino,
        second.st_mode,
    )


def _open_private_parent(path: Path, create: bool) -> tuple:
    _require_dir_fd_support()
    absolute = _canonicalize_root_alias(
        Path(os.path.abspath(os.fspath(path)))
    )
    if absolute == Path(absolute.anchor) or not absolute.name:
        raise ValueError("private JSON path must not be a filesystem root")
    root_fd = os.open(absolute.anchor, _directory_flags())
    parent_fd = None
    try:
        parent_fd = _open_relative_directory(
            root_fd,
            absolute.parts[1:-1],
            create=create,
        )
        parent_mode = os.fstat(parent_fd).st_mode
        if not stat.S_ISDIR(parent_mode):
            raise ValueError("private JSON parent must be a directory")
        if os.name == "posix" and parent_mode & 0o077:
            raise ValueError("private JSON parent must use owner-only permissions")
        return absolute, root_fd, parent_fd
    except BaseException:
        _close_descriptors(parent_fd, root_fd)
        raise


def ensure_private_directory_anchored(path: Path) -> None:
    """Create one owner-only directory through no-follow directory descriptors."""
    _require_dir_fd_support()
    absolute = _canonicalize_root_alias(
        Path(os.path.abspath(os.fspath(path)))
    )
    if absolute == Path(absolute.anchor):
        raise ValueError("private directory must not be a filesystem root")
    root_fd = os.open(absolute.anchor, _directory_flags())
    directory_fd = None
    try:
        directory_fd = _open_relative_directory(
            root_fd,
            absolute.parts[1:],
            create=True,
        )
        item = os.fstat(directory_fd)
        if not stat.S_ISDIR(item.st_mode):
            raise ValueError("private workspace node must be a directory")
        if os.name == "posix":
            os.fchmod(directory_fd, 0o700)
        _require_declared_directory_identity(
            root_fd,
            absolute,
            directory_fd,
            "private",
        )
    finally:
        _close_descriptors(directory_fd, root_fd)


def require_private_json_target(path: Path) -> None:
    """Fail closed unless a private JSON target is missing or a regular file."""
    absolute, root_fd, parent_fd = _open_private_parent(path, create=False)
    try:
        _private_target_stat(parent_fd, absolute.name)
        _require_declared_directory_identity(
            root_fd,
            absolute.parent,
            parent_fd,
            "private",
        )
    finally:
        _close_descriptors(parent_fd, root_fd)


def invalidate_private_json_anchored(path: Path) -> None:
    """Atomically remove a stale private JSON result through anchored descriptors."""
    absolute, root_fd, parent_fd = _open_private_parent(path, create=True)
    transaction_name = ""
    transaction_fd = None
    try:
        initial = _private_target_stat(parent_fd, absolute.name)
        if initial is not None:
            transaction_name, transaction_fd = _allocate_transaction_directory(
                parent_fd,
                f"{absolute.name}-invalidation",
            )
            try:
                os.rename(
                    absolute.name,
                    "stale",
                    src_dir_fd=parent_fd,
                    dst_dir_fd=transaction_fd,
                )
            except FileNotFoundError as error:
                raise ValueError(
                    "private JSON target changed during invalidation"
                ) from error
            moved = os.stat(
                "stale",
                dir_fd=transaction_fd,
                follow_symlinks=False,
            )
            if not _same_entry(initial, moved):
                raise ValueError("private JSON target changed during invalidation")
            os.fsync(parent_fd)
        if _private_target_stat(parent_fd, absolute.name) is not None:
            raise ValueError("private JSON target changed during invalidation")
        _require_declared_directory_identity(
            root_fd,
            absolute.parent,
            parent_fd,
            "private",
        )
    finally:
        first_error = None
        try:
            _close_descriptors(transaction_fd)
        except BaseException as error:
            first_error = error
        if transaction_name:
            try:
                _remove_tree_at(parent_fd, transaction_name)
                os.fsync(parent_fd)
            except BaseException as error:
                if first_error is None:
                    first_error = error
        try:
            _close_descriptors(parent_fd, root_fd)
        except BaseException as error:
            if first_error is None:
                first_error = error
        if first_error is not None:
            raise first_error


def _write_private_json_at(
    parent_fd: int,
    name: str,
    value: object,
    *,
    require_missing: bool = False,
) -> None:
    descriptor = None
    temporary = ""
    linked = False
    completed = False
    try:
        initial = _private_target_stat(parent_fd, name)
        if require_missing and initial is not None:
            raise ValueError("private JSON target must not already exist")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
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
            raise FileExistsError("could not allocate a private JSON temporary file")
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())

        current = _private_target_stat(parent_fd, name)
        if not _same_entry(initial, current):
            raise ValueError("private JSON target changed during write")
        if require_missing:
            os.link(
                temporary,
                name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            linked = True
            os.unlink(temporary, dir_fd=parent_fd)
        else:
            os.replace(
                temporary,
                name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        temporary = ""
        final = _private_target_stat(parent_fd, name)
        if final is None or (os.name == "posix" and final.st_mode & 0o077):
            raise ValueError("private JSON target must use owner-only permissions")
        os.fsync(parent_fd)
        completed = True
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
            if require_missing and linked and not completed:
                try:
                    os.unlink(name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
                except FileNotFoundError:
                    pass


def write_private_json_anchored(
    path: Path,
    value: object,
    *,
    require_missing: bool = False,
) -> None:
    """Atomically replace owner-only JSON through anchored no-follow descriptors."""
    absolute, root_fd, parent_fd = _open_private_parent(path, create=True)
    published = False
    completed = False
    try:
        _write_private_json_at(
            parent_fd,
            absolute.name,
            value,
            require_missing=require_missing,
        )
        published = True
        _require_declared_directory_identity(
            root_fd,
            absolute.parent,
            parent_fd,
            "private",
        )
        completed = True
    finally:
        try:
            if require_missing and published and not completed:
                try:
                    os.unlink(absolute.name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
                except FileNotFoundError:
                    pass
        finally:
            _close_descriptors(parent_fd, root_fd)


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


def _remove_tree_at(parent_fd: int, name: str) -> None:
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode):
        directory_fd = os.open(name, _directory_flags(), dir_fd=parent_fd)
        try:
            for child in os.listdir(directory_fd):
                _remove_tree_at(directory_fd, child)
        finally:
            os.close(directory_fd)
        os.rmdir(name, dir_fd=parent_fd)
    else:
        os.unlink(name, dir_fd=parent_fd)


def _allocate_transaction_directory(parent_fd: int, label: str) -> tuple:
    for _attempt in range(16):
        name = f".{label}.{secrets.token_hex(8)}.txn"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
        if os.fstat(descriptor).st_mode & 0o077:
            _close_descriptors(descriptor)
            _remove_tree_at(parent_fd, name)
            raise ValueError("transaction directory must be owner-only")
        return name, descriptor
    raise FileExistsError("could not allocate a transaction directory")


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
