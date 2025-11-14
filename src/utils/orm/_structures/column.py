import typing as t
from dataclasses import dataclass

from typing_extensions import TypeForm

from .. import _utils

if t.TYPE_CHECKING:
    from .._query import *
    from .model import Model


class Column[TOwner: Model, TValue](_utils.SqlString):
    _type: t.Final[tuple[TypeForm[TValue], ...]]
    _owner: t.Final[type[TOwner]]
    _name: t.Final[str]

    def __init__(self, types: tuple[TypeForm[TValue], ...]) -> None:
        self._type = types

    def __set_name__(self, owner: type[TOwner], name: str) -> None:
        _utils.validate_identifier(name)

        self._owner = owner  # type: ignore
        self._name = name  # type: ignore

    @t.overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass

    @t.overload
    def __get__(self, instance: None, owner: type[TOwner]) -> t.Self:
        pass

    @t.overload
    def __get__(
        self, instance: _NonDescriptorTypes, owner: type[_NonDescriptorTypes]
    ) -> t.Self:
        pass

    def __get__(
        self,
        instance: _NonDescriptorTypes | TOwner | None,
        owner: type[_NonDescriptorTypes | TOwner],
    ) -> t.Self | TValue:
        if instance is None or isinstance(instance, _NON_DESCRIPTOR_TYPES):
            return self

        return instance._columns_data[self._name]

    def __str__(self) -> str:
        return f"{self._owner}.`{self._name}`"

    @property
    def name(self) -> str:
        return self._name

    @property
    def owner(self) -> type[TOwner]:
        return self._owner

    @property
    def type(self) -> tuple[TypeForm[TValue], ...]:
        return self._type

    def set(self, value: TValue, /) -> ColumnSet[TOwner, TValue]:
        return ColumnSet(self, value)

    def bind(self, value: TValue, /, *values: TValue) -> ColumnBind[TOwner, TValue]:
        return ColumnBind(self, (value, *values))


def column[TOwner: Model, TValue](
    *fetch_types: TypeForm[TValue],
) -> t.Callable[[t.Callable[[TOwner], None]], Column[TOwner, TValue]]:
    def decorator(_: t.Callable[[TOwner], None]) -> Column[TOwner, TValue]:
        return Column(fetch_types)

    return decorator


@dataclass(frozen=True, slots=True)
class ColumnSet[TOwner: Model, TValue]():
    column: Column[TOwner, TValue]
    value: TValue

    def __iter__(self) -> t.Iterator[Column[TOwner, TValue] | TValue]:
        return iter((self.column, self.value))


@dataclass(frozen=True, slots=True)
class ColumnBind[TOwner: Model, TValue]:
    column: Column[TOwner, TValue]
    values: _utils.TupleOfOneOrMore[TValue]

    def __iter__(
        self,
    ) -> t.Iterator[Column[TOwner, TValue] | _utils.TupleOfOneOrMore[TValue]]:
        return iter((self.column, self.values))


type _NonDescriptorTypes = ColumnSet[t.Any, t.Any] | ColumnBind[t.Any, t.Any]

_NON_DESCRIPTOR_TYPES = (ColumnSet, ColumnBind)

__all__ = ["Column", "column", "ColumnSet", "ColumnBind"]
