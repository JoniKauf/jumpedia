import typing as t

from .._utils import TupleOfOneOrMore
from . import ExecutableQuery, FetchableQuery, utils

if t.TYPE_CHECKING:
    from ..structures.column import Column, ColumnBindedN
    from ..structures.model import Model


class InsertQuery[T: Model](ExecutableQuery[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedN], bool]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_entire_insert_sql(self._table, self._insert)


class InsertReturningQuery[T: Model](FetchableQuery[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedN], bool]
    _returning: TupleOfOneOrMore[Column[t.Any, t.Any]]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_added_returning_sql(
            self._returning, *utils.get_entire_insert_sql(self._table, self._insert)
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

    def returning(
        self, column: Column[t.Any, t.Any], /, *columns: Column[t.Any, t.Any]
    ) -> Returning[T]:
        return Returning(self._cursor, self._table, self._insert, (column, *columns))


__all__ = []
