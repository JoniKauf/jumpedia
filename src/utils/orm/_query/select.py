import typing as t

from .._utils import TupleOfOneOrMore
from . import FetchableQuery, Operator, Order, _utils

if t.TYPE_CHECKING:
    from .._structures.column import Column
    from .._structures.model import Model


class SelectQuery[T: Model](FetchableQuery[T]):
    _select: tuple[Column[t.Any, t.Any], ...]
    _where: TupleOfOneOrMore[tuple[t.Any, Operator, t.Any]] | None
    _order_by: TupleOfOneOrMore[tuple[Column[t.Any, t.Any], Order]] | None
    _limit: tuple[int, int] | None

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        params: list[t.Any] = []
        parts: list[str] = [
            "SELECT",
            (
                "*"
                if not self._select
                else ",".join(col._sql_str() for col in self._select)
            ),
            "FROM",
            self._table._sql_str(),
        ]

        _utils.handle_where_sql(self._where, parts, params)

        _utils.handle_order_by_sql(self._order_by, parts)

        _utils.handle_limit_sql(self._limit, parts)

        return (" ".join(parts), params)


class Limit[T: Model](SelectQuery[T]):
    @property
    def query(self) -> SelectQuery[T]:
        return SelectQuery(
            self._cursor,
            self._table,
            self._select,
            self._where,
            self._order_by,
            self._limit,
        )


class OrderBy[T: Model](Limit[T]):
    def limit(self, limit: int, /, *, offset: int = 0) -> Limit[T]:
        return Limit(
            self._cursor,
            self._table,
            self._select,
            self._where,
            self._order_by,
            (limit, offset),
        )


class Where[T: Model](OrderBy[T]):
    def order_by(
        self,
        column_order: tuple[Column[t.Any, t.Any], Order],
        /,
        *column_orders: tuple[Column[t.Any, t.Any], Order],
    ) -> OrderBy[T]:
        return OrderBy(
            self._cursor,
            self._table,
            self._select,
            self._where,
            (column_order, *column_orders),
            None,
        )


class Select[T: Model](Where[T]):
    def where(
        self,
        comparison: tuple[t.Any, Operator, t.Any],
        /,
        *comparisons: tuple[t.Any, Operator, t.Any],
    ) -> Where[T]:
        return Where(
            self._cursor,
            self._table,
            self._select,
            (comparison, *comparisons),
            None,
            None,
        )
