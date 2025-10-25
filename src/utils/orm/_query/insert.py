import typing as t

from .._utils import TupleOfOneOrMore
from . import ExecutableQuery, FetchableQuery, QueryData, utils

if t.TYPE_CHECKING:
    from .._structures.column import Column, ColumnBindedMany
    from .._structures.model import Model


class InsertQuery[T: Model](ExecutableQuery[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedMany], bool]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_entire_insert_sql(self._table, self._insert)


class InsertReturningQuery[T: Model](FetchableQuery[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedMany], bool]
    _returning: TupleOfOneOrMore[Column[T, t.Any]]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_added_returning_sql(
            self._returning, *utils.get_entire_insert_sql(self._table, self._insert)
        )


class Returning[T: Model](QueryData[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedMany], bool]
    _returning: TupleOfOneOrMore[Column[T, t.Any]]

    def query(self) -> InsertReturningQuery[T]:
        return InsertReturningQuery(
            self._cursor, self._table, self._insert, self._returning
        )


class Insert[T: Model](QueryData[T]):
    _insert: tuple[TupleOfOneOrMore[ColumnBindedMany], bool]

    def query(self) -> InsertQuery[T]:
        return InsertQuery(self._cursor, self._table, self._insert)

    def returning(
        self, column: Column[T, t.Any], /, *columns: Column[T, t.Any]
    ) -> Returning[T]:
        return Returning(self._cursor, self._table, self._insert, (column, *columns))


def __main():
    import textwrap

    INSERT = textwrap.dedent(
        """
        @t.overload
        def insert[T: Model](column_binded: ColumnBinded{0}, /, *columns_binded: ColumnBinded{0}, into: type[T], ignore: bool = False) -> Insert[T]:
            pass
    """
    )

    COUNT = 32

    for i in range(1, COUNT + 1):
        n = str(i).zfill(len(str(COUNT)))

        print(INSERT.format(n))


if __name__ == "__main__":
    __main()


__all__ = []
