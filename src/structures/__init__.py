from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from threading import RLock
from typing import Any, dataclass_transform
from contextlib import _GeneratorContextManager
from utils import locked, text

type StructuresTypeT = type[BaseStructure] | tuple[
    type[BaseStructure], *tuple[type[BaseStructure], ...]
]

_cls_names: dict[str, type["BaseStructure"]] = {}


def get_structure_types() -> tuple[type["BaseStructure"], ...]:
    return tuple(_cls_names.values())


@dataclass_transform(frozen_default=True, kw_only_default=True)
class _StructureMeta(ABCMeta):
    """Metaclass of all structures.

    It combines ABC and dataclass(frozen=True, kw_only=True) behaviour,
    with support for typing.
    """

    def __new__(
        mcls: type[_StructureMeta],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwargs: Any,
    ) -> _StructureMeta:
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        return dataclass(frozen=True, kw_only=True)(cls)  # type: ignore

    @cached_property
    def structure_name(self) -> str:
        return text.pascal_to_snake(self.__name__, delim=" ")


class BaseStructure(metaclass=_StructureMeta):
    @property
    def locked(self) -> _GeneratorContextManager[RLock, None, None]:
        return locked.equality_locked(self)

    @property
    @abstractmethod
    def identity(self) -> tuple[int, ...]:
        """Uniquely identify an object of this type."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    def __hash__(self) -> int:
        return hash(self.identity)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, BaseStructure):
            print(f"Compared", value, "to", self)
            return NotImplemented

        return self.__class__ is value.__class__ and self.identity == value.identity
