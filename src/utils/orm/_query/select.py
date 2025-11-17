import typing as t
from . import FetchableQuery, Operator, Order, utils

from .._structures.column import Column
from .._structures.model import Model


class SelectQuery[T: Model](FetchableQuery[T]):
    _select: tuple[Column[T, t.Any], ...]
    _where: list[tuple[tuple[t.Any, Operator, t.Any], ...]]
    _order_by: tuple[Column[T, t.Any] | tuple[Column[T, t.Any], Order], ...]
    _limit: tuple[int, int] | None

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        params: list[t.Any] = []
        parts: list[str] = ["SELECT"]

        parts.append(
            "*" if not self._select else ",".join(str(col) for col in self._select)
        )

        parts.append("FROM")
        parts.append(str(self._table))

        utils.handle_where_sql(self._where, parts, params)

        utils.handle_order_by_sql(self._order_by, parts)

        utils.handle_limit_sql(self._limit, parts)

        return (" ".join(parts), params)


class _LimitAndLater[T: Model](SelectQuery[T]):
    def limit(self, limit: int, /, *, offset: int = 0) -> Limit[T]:
        return Limit(
            self._table, self._select, self._where, self._order_by, (limit, offset)
        )


class _OrderByAndLater[T: Model](_LimitAndLater[T]):
    def order_by(
        self,
        column_order: Column[T, t.Any] | tuple[Column[T, t.Any], Order],
        /,
        *column_orders: Column[T, t.Any] | tuple[Column[T, t.Any], Order],
    ) -> OrderBy[T]:
        return OrderBy(
            self._table,
            self._select,
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
            self._select,
            [(comparison, *and_comparisons)],
            self._order_by,
            self._limit,
        )


class Limit[T: Model](SelectQuery[T]):
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
            self._table, self._select, self._where, self._order_by, self._limit
        )


class Select[T: Model](_WhereAndLater[T]):
    pass


__all__ = ["SelectQuery"]
