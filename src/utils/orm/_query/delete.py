import typing as t

from .._structures.column import Column
from .._structures.model import Model
from . import ExecutableQuery, FetchableQuery, Operator, Order, utils


class DeleteQuery[T: Model](ExecutableQuery[T]):
    _delete: bool
    _where: list[tuple[tuple[t.Any, Operator, t.Any], ...]]
    _order_by: tuple[Column[T, t.Any] | tuple[Column[T, t.Any], Order], ...]
    _limit: tuple[int, int] | None

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_entire_delete_sql(
            self._table, self._delete, self._where, self._order_by, self._limit
        )


class DeleteReturningQuery[T: Model](FetchableQuery[T]):
    _delete: bool
    _where: list[tuple[tuple[t.Any, Operator, t.Any], ...]]
    _order_by: tuple[Column[T, t.Any] | tuple[Column[T, t.Any], Order], ...]
    _limit: tuple[int, int] | None
    _returning: tuple[Column[T, t.Any], ...]

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        return utils.get_added_returning_sql(
            self._returning,
            *utils.get_entire_delete_sql(
                self._table, self._delete, self._where, self._order_by, self._limit
            ),
        )


class _ReturningAndLater[T: Model](DeleteQuery[T]):
    @t.overload
    def returning(self, all: t.Literal["*"], /) -> Returning[T]:
        pass

    @t.overload
    def returning(
        self, column: Column[t.Any, t.Any], /, *columns: Column[t.Any, t.Any]
    ) -> Returning[T]:
        pass

    def returning(
        self,
        all_or_column: Column[t.Any, t.Any] | t.Literal["*"],
        /,
        *columns: Column[t.Any, t.Any],
    ) -> Returning[T]:
        cols: tuple[Column[t.Any, t.Any], ...] = ()

        if isinstance(all_or_column, Column):
            cols = (all_or_column, *columns)

        return Returning(
            self._table, self._delete, self._where, self._order_by, self._limit, cols
        )


class _LimitAndLater[T: Model](_ReturningAndLater[T]):
    def limit(self, limit: int, /, *, offset: int = 0) -> Limit[T]:
        return Limit(
            self._table,
            self._delete,
            self._where,
            self._order_by,
            (limit, offset),
        )


class _OrderByAndLater[T: Model](_LimitAndLater[T]):
    def order_by(
        self,
        column_order: tuple[Column[t.Any, t.Any], Order],
        /,
        *column_orders: tuple[Column[t.Any, t.Any], Order],
    ) -> OrderBy[T]:
        return OrderBy(
            self._table,
            self._delete,
            self._where,
            (column_order, *column_orders),
            self._limit,
        )


class _WhereAndLater[T: Model](_OrderByAndLater[T]):
    def where(
        self,
        comparison: tuple[t.Any, Operator, t.Any],
        /,
        *and_comparisons: tuple[t.Any, Operator, t.Any],
    ) -> Where[T]:
        return Where(
            self._table,
            self._delete,
            [(comparison, *and_comparisons)],
            self._order_by,
            self._limit,
        )


class Returning[T: Model](DeleteReturningQuery[T]):
    pass


class Limit[T: Model](_ReturningAndLater[T]):
    pass


class OrderBy[T: Model](_LimitAndLater[T]):
    pass


class Where[T: Model](_OrderByAndLater[T]):
    def or_where(
        self,
        comparison: tuple[t.Any, Operator, t.Any],
        /,
        *and_comparisons: tuple[t.Any, Operator, t.Any],
    ) -> Where[T]:
        self._where.append((comparison, *and_comparisons))

        return Where(
            self._table, self._delete, self._where, self._order_by, self._limit
        )


class Delete[T: Model](_WhereAndLater[T]):
    pass


__all__ = ["DeleteQuery", "DeleteReturningQuery"]
