import typing as t
from dataclasses import dataclass
from functools import cached_property

from structures import BaseStructure
from utils import orm


@t.dataclass_transform(frozen_default=True)
class _AdapterMeta(type):
    def __new__(
        mcls: type[_AdapterMeta],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        /,
        **kwargs: t.Any,
    ) -> _AdapterMeta:
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        return dataclass(frozen=True)(cls)  # type: ignore


class BaseAdapter[T](metaclass=_AdapterMeta):
    _o: T

    @cached_property
    def _c(self) -> orm.Cursor:
        raise NotImplementedError()

    def __post_init__(self) -> None:
        if self.__class__ is BaseAdapter:
            raise TypeError

    def __eq__(self, value: object) -> bool:
        if type(self) != type(value):
            return NotImplemented

        return self._o == value._o  # type: ignore

    def __hash__(self) -> int:
        return hash(self._o)


class BaseStructureAdapter[T: BaseStructure](BaseAdapter[T]):
    @property
    def id(self) -> int:
        return self._o.id

    @property
    def name(self) -> str:
        return self._o.name

    def __str__(self) -> str:
        return self._o.name

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, self.__class__):
            return NotImplemented

        return self._o == value._o

    def mention(self) -> str:
        return type(self).do_mention(self._o)

    @classmethod
    def do_mention(cls, structure: BaseStructure) -> str:
        return f"{type(structure).type_name.lower()} {structure.name.lower()}"
