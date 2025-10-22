import typing as t
from dataclasses import dataclass

from .._utils import TagSafeSqlStr, TupleOfOneOrMore

if t.TYPE_CHECKING:
    from .._query import *
    from .model import Model


class Column[T](TagSafeSqlStr):
    def __init__(self, owner: type[Model], name: str, type: type[T]) -> None:
        self._owner = owner
        self._name = name
        self._type = type

    @t.overload
    def __get__(self, instance: Model, owner: type[Model]) -> T:
        pass

    @t.overload
    def __get__(self, instance: None, owner: type[Model]) -> t.Self:
        pass

    @t.overload
    def __get__(
        self, instance: ColumnBindedMany, owner: type[ColumnBindedMany]
    ) -> t.Self:
        pass

    def __get__(
        self,
        instance: ColumnBindedMany | Model | None,
        owner: type[ColumnBindedMany | Model],
    ) -> t.Self | T:
        if instance is None or isinstance(instance, ColumnBindedMany):
            return self

        return instance._columns_data[self._name]

    def __str__(self) -> str:
        return f"{self._owner}.`{self._name}`"

    @t.overload
    def bind(self, value: T, /) -> ColumnBindedSingle[T]:
        pass

    @t.overload
    def bind(self, value1: T, value2: T, /, *values: T) -> ColumnBindedMany[T]:
        pass

    def bind(self, value: T, /, *values: T) -> ColumnBindedMany[T]:
        return ColumnBindedMany(self, (value, *values))


@dataclass(frozen=True, slots=True)
class ColumnBindedMany[T]:
    column: Column[T]
    values: TupleOfOneOrMore[T]  # type: ignore

    def __iter__(self) -> t.Iterator[Column[T] | TupleOfOneOrMore[T]]:
        return iter((self.column, self.values))


@dataclass(frozen=True, slots=True)
class ColumnBindedSingle[T](ColumnBindedMany[T]):
    values: tuple[T]


__all__ = ["Column"]
