import typing as t

from .._utils import TupleOfOneOrMore
from . import ExecutableQuery, FetchableQuery, _utils

if t.TYPE_CHECKING:
    from .._structures.column import Column, ColumnBindedN
    from .._structures.model import Model


class InsertQuery[T: Model](ExecutableQuery[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedN], bool]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return _utils.get_entire_insert_sql(self._table, self._insert)


class InsertReturningQuery[T: Model](FetchableQuery[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedN], bool]
    _returning: tuple[Column[t.Any, t.Any], ...]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return _utils.get_added_returning_sql(
            self._returning, *_utils.get_entire_insert_sql(self._table, self._insert)
        )


class Returning[T: Model](InsertReturningQuery[T]):
    @property
    def query(self) -> InsertReturningQuery[T]:
        return InsertReturningQuery(
            self._cursor, self._table, self._insert, self._returning
        )


class Insert[T: Model](InsertQuery[T]):
    @property
    def query(self) -> InsertQuery[T]:
        return InsertQuery(self._cursor, self._table, self._insert)

    @t.overload
    def returning(
        self, all: t.Literal['*'], /
    ) -> Returning[T]:
        pass

    @t.overload
    def returning(
        self, column: Column[t.Any, t.Any], /, *columns: Column[t.Any, t.Any]
    ) -> Returning[T]:
        pass

    def returning(
        self, all_or_column: Column[t.Any, t.Any] | t.Literal["*"], /, *columns: Column[t.Any, t.Any]
    ) -> Returning[T]:
        cols: tuple[Column[t.Any, t.Any], ...] = ()

        if isinstance(all_or_column, Column):
            cols = (all_or_column, *columns)
        elif all_or_column != "*":
            raise ValueError
        
        return Returning(self._cursor, self._table, self._insert, cols)
