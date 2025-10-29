import enum
import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

if t.TYPE_CHECKING:
    from .._structures.model import Model


class Operator(enum.StrEnum):
    EQ = "="
    NEQ = "<>"


class Order(enum.StrEnum):
    ASC = enum.auto()
    DESC = enum.auto()


@t.dataclass_transform(eq_default=False, frozen_default=True)
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
        return dataclass(eq=False, frozen=True)(cls)


class Query[T: Model](metaclass=_QueryMeta):
    _table: t.Final[type[T]]

    @abstractmethod
    def _to_sql(self) -> tuple[str, list[t.Any]]:
        pass


class FetchableQuery[T: Model](Query[T]):
    pass


class ExecutableQuery[T: Model](Query[T]):
    pass


__all__ = ["Query", "FetchableQuery", "ExecutableQuery", "Operator", "Order"]
