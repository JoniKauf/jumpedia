
from ast import Return
import typing as t

from . import QueryMeta, Comparer, Order
from .._utils import TupleOfOneOrMore
from dataclasses import field

if t.TYPE_CHECKING:
    from .._model import BaseModel, Column


class ColumnBinded[T](t.NamedTuple):
    column: Column[T]
    insert: TupleOfOneOrMore[T]


class InsertQuery(metaclass=QueryMeta):
    _table: BaseModel
    _insert: tuple[TupleOfOneOrMore[ColumnBinded], bool]
    _returning: TupleOfOneOrMore[Column[t.Any]] | None

    def _to_sql(self) -> str:
        params: list[t.Any] = []
        parts: list[str] = []

        insert: list[str] = ["INSERT"]

        columns_binded, ignore = self._insert
        
        cols, binded = tuple(zip(*columns_binded))
        cols: TupleOfOneOrMore[Column[t.Any]]
        binded: TupleOfOneOrMore[TupleOfOneOrMore[t.Any]]

        if ignore:
            insert.append("IGNORE")
        
        insert.append("(" + ','.join(map(str, cols)) + ")")
        insert.append("VALUES")

        rows = zip(*binded)
        insert.append(f"({})")

        # Add executemany support 

        
        

class Returning(InsertQuery):
    def query(self) -> InsertQuery:
        return InsertQuery(
            self._table,
            self._insert,
            self._returning
        )

class Insert(Returning):
    _returning: None = field(init=False, default=None) # type: ignore

    def returning(self, column: Column[t.Any], /, *columns: Column[t.Any]) -> Returning:
        return Returning(
            self._table,
            self._insert,
            (column, *columns)
        )