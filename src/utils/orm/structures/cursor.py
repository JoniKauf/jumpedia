import typing as t
from types import TracebackType

import mariadb

from ..query.delete import Delete
from ..query.insert import Insert
from ..query.select import Select
from ..query.update import Update
from .column import Column, ColumnBindedOne, ColumnBindedOne, ColumnBindedN

if t.TYPE_CHECKING:
    from .model import Model

class Cursor:
    def __init__(self, cursor: mariadb.Cursor) -> None:
        self._mariadb_cursor = cursor

    def __enter__(self) -> Cursor:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        conn = t.cast(mariadb.Connection, self._mariadb_cursor.connection)

        if not conn.autocommit:
            if exc_value is None:
                conn.commit()
            else:
                conn.rollback()

        # Re-raise exception if occurred implicitly


    @t.overload
    def select[T: Model](self, all: t.Literal["*"], /, *, from_: type[T]) -> Select[T]:
        pass

    @t.overload
    def select[T: Model](
        self, column: Column[T, t.Any], /, *columns: Column[T, t.Any], from_: type[T]
    ) -> Select[T]:
        pass

    def select[T: Model](
        self,
        all_or_column: Column[T, t.Any] | t.Literal["*"],
        /,
        *columns: Column[T, t.Any],
        from_: type[T],
    ) -> Select[T]:
        cols: tuple[Column[T, t.Any], ...] = ()

        if isinstance(all_or_column, Column):
            cols = (all_or_column, *columns)
        elif all_or_column != "*":
            raise ValueError

        return Select(self, from_, cols, None, None, None)

    def insert[T: Model](
        self,
        column_binded: ColumnBindedN[T, t.Any],
        /,
        *columns_binded: ColumnBindedN[T, t.Any],
        into: type[T],
        ignore: bool = False,
    ) -> Insert[T]:
        return Insert(self, into, ((column_binded, *columns_binded), ignore))

    def update[T: Model](
        self,
        column_binded: ColumnBindedOne[T, t.Any],
        /,
        *columns_binded: ColumnBindedOne[T, t.Any],
        table: type[T],
        ignore: bool = False,
    ) -> Update[T]:
        return Update(
            self, table, ((column_binded, *columns_binded), ignore), None, None, None
        )

    def delete[T: Model](self, *, from_: type[T], ignore: bool = False) -> Delete[T]:
        return Delete(self, from_, ignore, None, None, None)

    def raw_execute(self, sql: str, params: t.Sequence[t.Any] = ()) -> None:
        self._mariadb_cursor.execute(sql, params)

    def raw_fetchone(self) -> t.Any:
        return self._mariadb_cursor.fetchone()

    def raw_fetchall(self) -> list[dict[str, t.Any]]:
        return self._mariadb_cursor.fetchall()


__all__ = ["Cursor"]
