"""Anchored directory-FD I/O for controlled pilot evidence."""

from __future__ import annotations

import inspect
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Dict, Set


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
    and all(
        function in os.supports_dir_fd
        for function in (os.open, os.mkdir, os.stat, os.unlink)
    )
    and os.stat in os.supports_follow_symlinks
    and os.listdir in os.supports_fd
    and _replace_supports_dir_fd()
)


def _require_dir_fd_support() -> None:
    if not _DIR_FD_SUPPORTED:
        raise ValueError("secure directory-fd evidence writes are not supported")


def _directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


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


def _open_output_directory(output_dir: Path) -> tuple:
    path = Path(os.path.abspath(os.fspath(output_dir)))
    if path == Path(path.anchor):
        raise ValueError("evidence output must not be a filesystem root")
    root_descriptor = os.open(path.anchor, _directory_flags())
    descriptor = None
    try:
        descriptor = _open_relative_directory(
            root_descriptor,
            path.parts[1:],
            create=True,
        )
        return path, root_descriptor, descriptor
    except BaseException:
        _close_descriptors(descriptor, root_descriptor)
        raise


def read_json_anchored(path: Path):
    _require_dir_fd_support()
    absolute = Path(os.path.abspath(os.fspath(path)))
    if absolute == Path(absolute.anchor):
        raise ValueError("anchored JSON path must not be a filesystem root")
    root_descriptor = os.open(absolute.anchor, _directory_flags())
    parent_descriptor = None
    file_descriptor = None
    try:
        parent_descriptor = _open_relative_directory(
            root_descriptor,
            absolute.parts[1:-1],
            create=False,
        )
        try:
            file_descriptor = os.open(
                absolute.name,
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=parent_descriptor,
            )
        except FileNotFoundError:
            raise
        except OSError as error:
            raise ValueError(
                "anchored JSON file must not be a symbolic link or non-regular file"
            ) from error
        if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
            raise ValueError("anchored JSON file must be a regular file")
        handle = os.fdopen(file_descriptor, "r", encoding="utf-8")
        file_descriptor = None
        with handle:
            return json.load(handle)
    finally:
        _close_descriptors(file_descriptor, parent_descriptor, root_descriptor)


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


def _require_declared_output_identity(
    root_fd: int,
    output: Path,
    anchored_output_fd: int,
) -> None:
    _require_declared_directory_identity(
        root_fd,
        output,
        anchored_output_fd,
        "output",
    )


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
    absolute = Path(os.path.abspath(os.fspath(path)))
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


def write_private_json_anchored(
    path: Path,
    value: object,
    *,
    require_missing: bool = False,
) -> None:
    """Atomically replace owner-only JSON through anchored no-follow descriptors."""
    absolute, root_fd, parent_fd = _open_private_parent(path, create=True)
    descriptor = None
    temporary = ""
    published = False
    completed = False
    try:
        initial = _private_target_stat(parent_fd, absolute.name)
        if require_missing and initial is not None:
            raise ValueError("private JSON target must not already exist")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        for _attempt in range(16):
            temporary = f".{absolute.name}.{secrets.token_hex(8)}.tmp"
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
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())

        current = _private_target_stat(parent_fd, absolute.name)
        if not _same_entry(initial, current):
            raise ValueError("private JSON target changed during write")
        os.replace(
            temporary,
            absolute.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        temporary = ""
        published = True
        final = _private_target_stat(parent_fd, absolute.name)
        if final is None or (os.name == "posix" and final.st_mode & 0o077):
            raise ValueError("private JSON target must use owner-only permissions")
        os.fsync(parent_fd)
        _require_declared_directory_identity(
            root_fd,
            absolute.parent,
            parent_fd,
            "private",
        )
        completed = True
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
        finally:
            try:
                if temporary:
                    try:
                        os.unlink(temporary, dir_fd=parent_fd)
                    except FileNotFoundError:
                        pass
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


def _remove_stale_json_files(
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
            child = _open_child_directory(directory_fd, name, create=False)
            try:
                _remove_stale_json_files(child, expected, prefix + (name,))
            finally:
                os.close(child)
            continue
        if not stat.S_ISREG(item.st_mode):
            raise ValueError("evidence output descendants must be regular files")
        if name.endswith(".json") and relative not in expected:
            os.unlink(name, dir_fd=directory_fd)


def write_evidence_pack(output_dir: Path, pack: Dict[str, object]) -> Dict[str, object]:
    _require_dir_fd_support()
    output = Path(os.path.abspath(os.fspath(output_dir)))
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

    output, root_fd, output_fd = _open_output_directory(output)
    expected = {"/".join(components + (name,)) for components, name in files}
    try:
        for (components, name), item in files.items():
            parent_fd = _open_relative_directory(output_fd, components, create=True)
            try:
                _write_json_atomic(parent_fd, name, item)
            finally:
                os.close(parent_fd)
        _remove_stale_json_files(output_fd, expected)
        _require_declared_output_identity(root_fd, output, output_fd)
    finally:
        _close_descriptors(output_fd, root_fd)
    return {"status": "written", "file_count": len(files), "output_dir": str(output)}
