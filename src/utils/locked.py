import contextlib
import typing as t
from threading import RLock

_active_locks: dict[t.Hashable, t.Any] = {}  # make beartype happy
_ref_count: dict[t.Hashable, int] = {}
_locks_lock = RLock()


@contextlib.contextmanager
def equality_locked(obj: t.Hashable):
    """Lock objects that are equal with the same lock."""

    with _locks_lock:
        lock = _active_locks.setdefault(obj, RLock())
        _ref_count[obj] = _ref_count.get(obj, 0) + 1

    lock.acquire()

    try:
        yield lock
    finally:
        with _locks_lock:
            lock.release()

            _ref_count[obj] -= 1

            if _ref_count[obj] == 0:
                _ref_count.pop(obj)
                _active_locks.pop(obj)
