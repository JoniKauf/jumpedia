import enum
import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

if t.TYPE_CHECKING:
    from .._structures.cursor import Cursor
    from .._structures.model import Model


class Operator(enum.StrEnum):
    EQ = "="
    NEQ = "<>"


class Order(enum.StrEnum):
    ASC = enum.auto()
    DESC = enum.auto()


@t.dataclass_transform(eq_default=False)
class _QueryMeta(ABCMeta):
    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        /,
        **kwds: t.Any,
    ):
        cls = super().__new__(mcls, name, bases, namespace, **kwds)
        return dataclass(eq=False)(cls)


class QueryData[T: Model](metaclass=_QueryMeta):
    _cursor: Cursor
    _table: type[T]


class Query[T: Model](QueryData[T]):
    @abstractmethod
    def _to_sql(self) -> tuple[str, list[t.Any]]:
        pass

    def _core_execute(self) -> None:
        self._cursor._mariadb_cursor.execute(*self._to_sql())


class FetchableQuery[T: Model](Query[T]):
    def fetchone(self, query: FetchableQuery[T]) -> T | None:
        self._core_execute()

        fetch = t.cast(dict[str, t.Any] | None, self._cursor._mariadb_cursor.fetchone())

        if fetch is None:
            return None

        return query._table(fetch)

    def fetchall(self) -> list[T]:
        self._core_execute()

        fetch = t.cast(list[dict[str, t.Any]], self._cursor._mariadb_cursor.fetchone())

        return list(map(self._table, fetch))


class ExecutableQuery[T: Model](Query[T]):
    def execute(self) -> None:
        self._core_execute()


__all__ = [
    'Operator',
    'Order'
]
