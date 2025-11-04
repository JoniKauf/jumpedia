import typing as t

from . import ExecutableQuery, Operator, Order, utils

if t.TYPE_CHECKING:
    from .._structures.column import Column, ColumnSet
    from .._structures.model import Model


class UpdateQuery[T: Model](ExecutableQuery[T]):
    _update: tuple[tuple[ColumnSet[T, t.Any], ...], bool]
    _where: list[tuple[tuple[t.Any, Operator, t.Any], ...]]
    _order_by: tuple[tuple[Column[T, t.Any], Order], ...]
    _limit: tuple[int, int] | None

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        params: list[t.Any] = []
        parts: list[str] = ["UPDATE"]

        cols_binded, ignore = self._update

        if ignore:
            parts.append("IGNORE")

        parts.append(str(self._table))

        parts.append("SET")

        parts.append(
            ",".join(f"{col}={utils.placehold(v, params)}" for col, v in cols_binded)
        )

        utils.handle_where_sql(self._where, parts, params)

        utils.handle_order_by_sql(self._order_by, parts)

        utils.handle_limit_sql(self._limit, parts)

        return (" ".join(parts), params)


class _LimitAndLater[T: Model](UpdateQuery[T]):
    def limit(self, limit: int, /, *, offset: int = 0) -> Limit[T]:
        return Limit(
            self._table,
            self._update,
            self._where,
            self._order_by,
            (limit, offset),
        )


class _OrderByAndLater[T: Model](_LimitAndLater[T]):
    def order_by(
        self,
        column_order: tuple[Column[T, t.Any], Order],
        /,
        *column_orders: tuple[Column[T, t.Any], Order],
    ) -> OrderBy[T]:
        return OrderBy(
            self._table,
            self._update,
            self._where,
            (column_order, *column_orders),
            None,
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
            self._update,
            [(comparison, *and_comparisons)],
            self._order_by,
            self._limit,
        )


class Limit[T: Model](UpdateQuery[T]):
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
            self._table, self._update, self._where, self._order_by, self._limit
        )


class Update[T: Model](_WhereAndLater[T]):
    pass


__all__ = ["UpdateQuery"]
