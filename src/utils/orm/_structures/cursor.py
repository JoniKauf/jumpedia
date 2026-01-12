import itertools
import typing as t
from dataclasses import dataclass
from types import TracebackType

import mariadb

from .._query import ExecutableQuery, FetchableQuery, Query
from .._query.insert import InsertQuery, InsertReturningQuery

if t.TYPE_CHECKING:
    from .connector import Connector
    from .model import Model


@dataclass(frozen=True, slots=True)
class ExecuteData[T1: int | None, T2: int | None]:
    last_generated_id: T1
    affected_row_count: T2


class Cursor:
    def __init__(self, connector: Connector, connection: mariadb.Connection) -> None:
        self._connector: Connector = connector
        self._mariadb_connection = connection
        self._mariadb_cursor = connection.cursor(dictionary=True)

    def __enter__(self) -> Cursor:
        self._connector._existing_refs += 1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self._mariadb_connection.autocommit:
            if exc_value is None:
                self._mariadb_connection.commit()
            else:
                self._mariadb_connection.rollback()

        self._mariadb_cursor.close()

        self._connector._existing_refs -= 1

        if self._connector._existing_refs <= 0:
            self._mariadb_connection.close()
            self._connector._existing_refs = 0
            self._connector._existing_conn = None

    def _core_execute(self, query: Query, /) -> None:
        sql, data = query._to_sql()

        if isinstance(query, (InsertQuery, InsertReturningQuery)):
            self._mariadb_cursor.executemany(sql, data)
        else:
            self._mariadb_cursor.execute(sql, data)

    @t.overload
    def execute(
        self,
        query: ExecutableQuery,
        /,
        *,
        get_last_generated_id: t.Literal[False] = False,
        get_affected_row_count: t.Literal[False] = False,
    ) -> ExecuteData[None, None]:
        pass

    @t.overload
    def execute(
        self, query: ExecutableQuery, /, *, get_last_generated_id: t.Literal[True]
    ) -> ExecuteData[int | None, None]:
        pass

    @t.overload
    def execute(
        self, query: ExecutableQuery, /, *, get_affected_row_count: t.Literal[True]
    ) -> ExecuteData[None, int]:
        pass

    @t.overload
    def execute(
        self,
        query: ExecutableQuery,
        /,
        *,
        get_last_generated_id: t.Literal[True],
        get_affected_row_count: t.Literal[True],
    ) -> ExecuteData[int | None, int]:
        pass

    def execute(
        self,
        query: ExecutableQuery,
        /,
        *,
        get_last_generated_id: bool = False,
        get_affected_row_count: bool = False,
    ) -> ExecuteData[t.Any, t.Any]:
        self._core_execute(query)

        match (get_last_generated_id, get_affected_row_count):
            case False, False:
                return ExecuteData(None, None)
            case True, False:
                return ExecuteData(self._mariadb_cursor.lastrowid, None)
            case False, True:
                return ExecuteData(None, self._mariadb_cursor.rowcount)
            case True, True:
                return ExecuteData(
                    self._mariadb_cursor.lastrowid,
                    self._mariadb_cursor.rowcount,
                )
            case _:
                t.assert_never((get_last_generated_id, get_affected_row_count))

    def fetch_one[T: Model](self, query: FetchableQuery[T], /) -> T | None:
        self._core_execute(query)

        fetch = t.cast(dict[str, t.Any] | None, self._mariadb_cursor.fetchone())

        if fetch is None:
            return None

        return query._table(fetch)

    def fetch_all[T: Model](self, query: FetchableQuery[T], /) -> list[T]:
        self._core_execute(query)

        fetch = t.cast(list[dict[str, t.Any]], self._mariadb_cursor.fetchall())

        return list(map(query._table, fetch))

    def raw_execute(self, sql: str, params: t.Sequence[t.Any] = ()) -> None:
        self._mariadb_cursor.execute(sql, params)

    def raw_fetchone(self) -> t.Any:
        return self._mariadb_cursor.fetchone()

    def raw_fetchall(self) -> list[dict[str, t.Any]]:
        return self._mariadb_cursor.fetchall()

    def commit(self) -> None:
        return self._mariadb_connection.commit()


__all__ = ["ExecuteData", "Cursor"]
