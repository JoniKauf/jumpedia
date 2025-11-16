import typing as t

from . import ExecutableQuery, FetchableQuery, utils

if t.TYPE_CHECKING:
    from .._structures.column import Column, ColumnBind
    from .._structures.model import Model


class InsertQuery[T: Model](ExecutableQuery[T]):
    _insert: tuple[tuple[ColumnBind[T, t.Any], ...], bool]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_entire_insert_sql(self._table, self._insert)


class InsertReturningQuery[T: Model](FetchableQuery[T]):
    _insert: tuple[tuple[ColumnBind[T, t.Any], ...], bool]
    _returning: tuple[Column[T, t.Any], ...]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_added_returning_sql(
            self._returning, *utils.get_entire_insert_sql(self._table, self._insert)
        )


class Returning[T: Model](InsertReturningQuery[T]):
    pass


class Insert[T: Model](InsertQuery[T]):
    @t.overload
    def returning(self, all: t.Literal["*"], /) -> Returning[T]:
        pass

    @t.overload
    def returning(
        self, column: Column[T, t.Any], /, *columns: Column[T, t.Any]
    ) -> Returning[T]:
        pass

    def returning(
        self,
        all_or_column: Column[T, t.Any] | t.Literal["*"],
        /,
        *columns: Column[T, t.Any],
    ) -> Returning[T]:
        from .._structures.column import Column

        cols: tuple[Column[T, t.Any], ...] = ()

        if isinstance(all_or_column, Column):
            cols = (all_or_column, *columns)

        return Returning(self._table, self._insert, cols)


__all__ = ["InsertQuery", "InsertReturningQuery"]
