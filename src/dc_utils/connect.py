import time
import typing as t

import mariadb

from utils import orm, secret

from . import errors

__DATA: secret.DatabaseConnectionData = secret.listen().DATABASE_CONNECTION_DATA


def _get_new_connection() -> mariadb.Connection:
    wait: float = 0.01
    TRIES = 5

    last_error: Exception | None = None

    for i in range(TRIES):
        try:
            return mariadb.connect(**__DATA)
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
