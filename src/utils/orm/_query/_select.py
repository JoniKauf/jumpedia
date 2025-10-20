from dataclasses import field
import typing as t

from . import QueryMeta, Comparer, Order
from .._utils import TupleOfOneOrMore, placehold

if t.TYPE_CHECKING:
    from .._model import BaseModel, Column

class SelectQuery(metaclass=QueryMeta):
    _table: BaseModel
    _select: tuple[Column[t.Any], ...]
    _where: TupleOfOneOrMore[tuple[t.Any, Comparer, t.Any]] | None
    _order_by: TupleOfOneOrMore[tuple[Column[t.Any], Order]] | None
    _limit: tuple[int, int] | None

    def _to_sql(self) -> tuple[str, list[t.Any]]:
        params: list[t.Any] = []
        parts: list[str] = [
            f"SELECT {'*' if not self._select else ','.join(map(str, self._select))} FROM {self._table}"
        ]
        
        if self._where is not None:
            parts.append("WHERE " + " AND ".join(
                f"{placehold(left, params)} {comp} {placehold(right, params)}"
                for left, comp, right in self._where
            ))
        
        if self._order_by is not None:
            parts.append("ORDER BY " + ','.join(
                f"{col} {order}" for col, order in self._order_by
            ))

        if self._limit is not None:
            offset = self._limit[1]
            offset_str = ""

            if offset > 0:
                offset_str = f" OFFSET {offset}"

            parts.append(f"LIMIT {self._limit[0]}" + offset_str)

        return ('\n'.join(parts), params)

class Limit(SelectQuery):
    def query(self) -> SelectQuery:
        return SelectQuery(
            self._table,
            self._select,
            self._where,
            self._order_by,
            self._limit
        )

class OrderBy(Limit):
    _limit: None = field(init=False, default=None) # type: ignore

    def limit(self, limit: int, /, offset: int = 0) -> Limit:
        return Limit(
            self._table,
            self._select,
            self._where,
            self._order_by,
            (limit, offset)
        )

class Where(OrderBy):
    _order_by: None = field(init=False, default=None) # type: ignore

    def order_by(self, column_order: tuple[Column[t.Any], Order], /, *column_orders: tuple[Column[t.Any], Order]) -> OrderBy:
        return OrderBy(
            self._table,
            self._select,
            self._where,
            (column_order, *column_orders)
        )
    
class Select(Where):
    _where: None = field(init=False, default=None) # type: ignore

    def where(self, comparison: tuple[t.Any, Comparer, t.Any], /, *comparisons: tuple[t.Any, Comparer, t.Any]) -> Where:
        return Where(
            self._table,
            self._select,
            (comparison, *comparisons)
        )
