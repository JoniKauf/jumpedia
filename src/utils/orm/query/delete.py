import typing as t

from .._utils import TupleOfOneOrMore
from . import (ExecutableQuery, FetchableQuery, Operator, Order, QueryData,
               utils)

if t.TYPE_CHECKING:
    from ..structures.column import Column
    from ..structures.model import Model


class DeleteQuery[T: Model](ExecutableQuery[T]):
    _delete: bool
    _where: TupleOfOneOrMore[tuple[t.Any, Operator, t.Any]] | None
    _order_by: TupleOfOneOrMore[tuple[Column[T, t.Any], Order]] | None
    _limit: tuple[int, int] | None

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_entire_delete_sql(
            self._table, self._delete, self._where, self._order_by, self._limit
        )


class DeleteReturningQuery[T: Model](FetchableQuery[T]):
    _delete: bool
    _returning: TupleOfOneOrMore[Column[T, t.Any]]
    _where: TupleOfOneOrMore[tuple[t.Any, Operator, t.Any]] | None
    _order_by: TupleOfOneOrMore[tuple[Column[T, t.Any], Order]] | None
    _limit: tuple[int, int] | None

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_added_returning_sql(
            self._returning,
            *utils.get_entire_delete_sql(
                self._table, self._delete, self._where, self._order_by, self._limit
            ),
        )


class Returning[T: Model](QueryData[T]):
    _delete: bool
    _returning: TupleOfOneOrMore[Column[T, t.Any]]
    _where: TupleOfOneOrMore[tuple[t.Any, Operator, t.Any]] | None
    _order_by: TupleOfOneOrMore[tuple[Column[T, t.Any], Order]] | None
    _limit: tuple[int, int] | None

    def query(self) -> DeleteReturningQuery[T]:
        return DeleteReturningQuery(
            self._cursor,
            self._table,
            self._delete,
            self._returning,
            self._where,
            self._order_by,
            self._limit,
        )


class Limit[T: Model](QueryData[T]):
    _delete: bool
    _where: TupleOfOneOrMore[tuple[t.Any, Operator, t.Any]] | None
    _order_by: TupleOfOneOrMore[tuple[Column[T, t.Any], Order]] | None
    _limit: tuple[int, int] | None

    def query(self) -> DeleteQuery[T]:
        return DeleteQuery(
            self._cursor,
            self._table,
            self._delete,
            self._where,
            self._order_by,
            self._limit,
        )

    def returning(
        self, column: Column[T, t.Any], /, *columns: Column[T, t.Any]
    ) -> Returning[T]:
        return Returning(
            self._cursor,
            self._table,
            self._delete,
            (column, *columns),
            self._where,
            self._order_by,
            self._limit,
        )


class OrderBy[T: Model](Limit[T]):
    def limit(self, limit: int, /, *, offset: int = 0) -> Limit[T]:
        return Limit(
            self._cursor,
            self._table,
            self._delete,
            self._where,
            self._order_by,
            (limit, offset),
        )


class Where[T: Model](OrderBy[T]):
    def order_by(
        self,
        column_order: tuple[Column[T, t.Any], Order],
        /,
        *column_orders: tuple[Column[T, t.Any], Order],
    ) -> OrderBy[T]:
        return OrderBy(
            self._cursor,
            self._table,
            self._delete,
            self._where,
            (column_order, *column_orders),
            None,
        )


class Delete[T: Model](Where[T]):
    def where(
        self,
        comparison: tuple[t.Any, Operator, t.Any],
        /,
        *comparisons: tuple[t.Any, Operator, t.Any],
    ) -> Where[T]:
        return Where(
            self._cursor,
            self._table,
            self._delete,
            (comparison, *comparisons),
            None,
            None,
        )


__all__ = []
