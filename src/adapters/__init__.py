import typing as t
from dataclasses import dataclass

from structures import BaseStructure


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
    _s: T

    def __post_init__(self) -> None:
        if self.__class__ is BaseAdapter:
            raise TypeError
