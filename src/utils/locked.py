import contextlib
import typing as t
from threading import RLock

_active_locks: dict[tuple[t.Hashable, type], RLock] = {}
_ref_count: dict[tuple[t.Hashable, type], int] = {}
_locks_lock = RLock()


@contextlib.contextmanager
def equality_locked(obj: t.Hashable) -> t.Generator[None]:
    """Lock objects that are equal with the same lock."""

    tup = (obj, type(obj))

    with _locks_lock:
        lock = _active_locks.setdefault(tup, RLock())
        _ref_count[tup] = _ref_count.get(tup, 0) + 1

    lock.acquire()

    try:
        yield
    finally:
        lock.release()

        with _locks_lock:
            _ref_count[tup] -= 1

            if _ref_count[tup] == 0:
                _ref_count.pop(tup)
                _active_locks.pop(tup, None)
