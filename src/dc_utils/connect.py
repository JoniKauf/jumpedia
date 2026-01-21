import time
import typing as t

import mariadb

from utils import orm, secret

from . import errors

__POOL: mariadb.ConnectionPool | None = None


def _get_pool() -> mariadb.ConnectionPool:
    global __POOL

    if __POOL is None:
        __POOL = mariadb.ConnectionPool(
            pool_name="pool", pool_size=10, **secret.listen().DATABASE_CONNECTION_DATA
        )

    return __POOL


def _get_new_connection() -> mariadb.Connection:
    wait: float = 0.01
    TRIES = 5

    last_error: Exception | None = None

    for i in range(TRIES):
        try:
            return _get_pool().get_connection()
        except mariadb.Error as e:
            if i < TRIES - 1:
                time.sleep(wait)
                wait *= 2
            else:
                last_error = e

    print(f"Error connecting: {last_error}")
    raise errors.DatabaseError()


def get_new_connection_cursor_adapter() -> orm.Cursor:
    return orm.Cursor(conn := _get_new_connection(), conn.cursor(dictionary=True))
