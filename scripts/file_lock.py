"""
File lock utility — prevents data loss from concurrent multi-process read/write of JSON files.

Usage:
    from file_lock import atomic_json_update, atomic_json_read

    # Atomic read
    data = atomic_json_read(path, default=[])

    # Atomic update (read → modify → write back, lock held throughout)
    def modifier(tasks):
        tasks.append(new_task)
        return tasks 
    atomic_json_update(path, modifier, default=[])
"""
import fcntl
import json
import os
import pathlib
import tempfile
from typing import Any, Callable


def _lock_path(path: pathlib.Path) -> pathlib.Path:
    return path.parent / (path.name + '.lock')


def atomic_json_read(path: pathlib.Path, default: Any = None) -> Any:
    """Acquire shared lock and read JSON file."""
    lock_file = _lock_path(path)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        try:
            return json.loads(path.read_text()) if path.exists() else default
        except Exception:
            return default
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def atomic_json_update(
    path: pathlib.Path,
    modifier: Callable[[Any], Any],
    default: Any = None,
) -> Any:
    """
    Atomically read → modify → write back a JSON file.
    modifier(data) should return the modified data.
    Uses temp file + rename to guarantee write atomicity.
    """
    lock_file = _lock_path(path)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        # Read
        try:
            data = json.loads(path.read_text()) if path.exists() else default
        except Exception:
            data = default
        # Modify
        result = modifier(data)
        # Atomic write via temp file + rename
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), suffix='.tmp', prefix=path.stem + '_'
        )
        try:
            with os.fdopen(tmp_fd, 'w') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(path))
        except Exception:
            os.unlink(tmp_path)
            raise
        return result
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def atomic_json_write(path: pathlib.Path, data: Any) -> None:
    """Atomically write JSON file (exclusive lock + tmpfile rename).
    Writes directly without reading existing content (avoids extra read overhead of atomic_json_update).
    """
    lock_file = _lock_path(path)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), suffix='.tmp', prefix=path.stem + '_'
        )
        try:
            with os.fdopen(tmp_fd, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(path))
        except Exception:
            os.unlink(tmp_path)
            raise
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
