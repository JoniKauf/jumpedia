import typing as t
from types import TracebackType

import mariadb

from .column import Column, ColumnBindedSingle
from .._query.delete import Delete
from .._query.insert import Insert
from .._query.select import Select
from .._query.update import Update

if t.TYPE_CHECKING:
    from .model import Model

class CursorContextManager:
    def __init__(self, cursor: Cursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> Cursor:
        return self._cursor

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        conn = t.cast(mariadb.Connection, self._cursor._mariadb_cursor.connection)

        if not conn.autocommit:
            if exc_value is None:
                conn.commit()
            else:
                conn.rollback()

        # Re-raise exception if occurred implicitly


class Cursor:
    def __init__(self, cursor: mariadb.Cursor) -> None:
        self._mariadb_cursor = cursor

    @t.overload
    def select[T: Model](self, all: t.Literal['*'], /, *, from_: type[T]) -> Select[T]:
        pass

    @t.overload
    def select[T: Model](self, column: Column[t.Any], /, *columns: Column[t.Any], from_: type[T]) -> Select[T]:
        pass

    def select[T: Model](
        self, all_or_column: Column[t.Any] | t.Literal['*'], /, *columns: Column[t.Any], from_: type[T]
    ) -> Select[T]:
        cols: tuple[Column[t.Any], ...] = ()

        if isinstance(all_or_column, Column):
            cols = (all_or_column, *columns)
        elif all_or_column != '*':
            raise ValueError
        
        return Select(self, from_, cols, None, None, None)

    def insert[T: Model](
        self,
        column_binded: ColumnBindedSingle[t.Any],
        /,
        *columns_binded: ColumnBindedSingle[t.Any],
        into: type[T],
        ignore: bool = False,
    ) -> Insert[T]:
        return Insert(self, into, ((column_binded, *columns_binded), ignore))

    def update[T: Model](
        self,
        column_binded: ColumnBindedSingle[t.Any],
        /,
        *columns_binded: ColumnBindedSingle[t.Any],
        table: type[T],
        ignore: bool = False,
    ) -> Update[T]:
        return Update(
            self, table, ((column_binded, *columns_binded), ignore), None, None, None
        )

    def delete[T: Model](self, *, from_: type[T], ignore: bool = False) -> Delete[T]:
        return Delete(self, from_, ignore, None, None, None)

__all__ = [
    'Cursor'
]
