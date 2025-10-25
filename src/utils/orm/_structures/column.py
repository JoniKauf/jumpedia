import functools
import typing as t
from dataclasses import dataclass
from typing_extensions import TypeForm

from .._utils import SqlString, TupleOfOneOrMore

if t.TYPE_CHECKING:
    from .._query import *
    from .model import Model


class Column[TOwner: Model, TValue](SqlString):
    def __init__(self, types: tuple[TypeForm[TValue], ...]) -> None:
        self._type = types

    def __set_name__(self, owner: type[TOwner], name: str) -> None:
        self._owner = owner
        self._name = name

    @t.overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass

    @t.overload
    def __get__(self, instance: None, owner: type[TOwner]) -> t.Self:
        pass

    @t.overload
    def __get__(
        self, instance: ColumnBindedMany, owner: type[ColumnBindedMany]
    ) -> t.Self:
        pass

    def __get__(
        self,
        instance: ColumnBindedMany | TOwner | None,
        owner: type[ColumnBindedMany | TOwner],
    ) -> t.Self | TValue:
        if instance is None or isinstance(instance, ColumnBindedMany):
            return self

        return instance._columns_data[self._name]

    def _sql_str(self) -> str:
        return f"{self._owner}.`{self._name}`"

    @t.overload
    def bind(self, value: TValue, /) -> ColumnBindedSingle[TOwner, TValue]:
        pass

    @t.overload
    def bind(self, value1: TValue, value2: TValue, /, *values: TValue) -> ColumnBindedMany[TOwner, TValue]:
        pass

    def bind(self, value: TValue, /, *values: TValue) -> ColumnBindedMany[TOwner, TValue]:
        return ColumnBindedMany(self, (value, *values))


def column[TOwner: Model, TValue](*fetch_types: TypeForm[TValue]) -> t.Callable[[t.Callable[[TOwner], None]], Column[TOwner, TValue]]:
    def decorator(_: t.Callable[[TOwner], None]) -> Column[TOwner, TValue]:
        return Column(fetch_types)
    
    return decorator

    


@dataclass(frozen=True, slots=True)
class ColumnBindedMany[TOwner: Model, TValue]:
    column: Column[TOwner, TValue]
    values: TupleOfOneOrMore[TValue]  # type: ignore

    def __iter__(self) -> t.Iterator[Column[TOwner, TValue] | TupleOfOneOrMore[TValue]]:
        return iter((self.column, self.values))


@dataclass(frozen=True, slots=True)
class ColumnBindedSingle[TOwner: Model, TValue](ColumnBindedMany[TOwner, TValue]):
    values: tuple[TValue]


__all__ = ["column"]