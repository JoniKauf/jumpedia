import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from utils import text

type StructuresTypeT = type[BaseStructure] | tuple[
    type[BaseStructure], *tuple[type[BaseStructure], ...]
]


@t.dataclass_transform(frozen_default=True, kw_only_default=True, eq_default=False)
class _StructureMeta(ABCMeta):
    """Metaclass of all structures.

    It combines ABC and dataclass(frozen=True, kw_only=True) behaviour,
    with support for typing.
    """

    def __new__(
        mcls: type[_StructureMeta],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        /,
        **kwargs: t.Any,
    ) -> _StructureMeta:
        cls = super().__new__(
            mcls, name, bases, namespace | {"_type_name": None}, **kwargs
        )

        if namespace.get("__dataclass_fields__") is None:
            return dataclass(frozen=True, slots=True, kw_only=True, eq=False)(cls)  # type: ignore

        return cls

    @property
    def type_name(self) -> str:
        v = getattr(self, "_type_name", None)

        if v is None:
            v = text.pascal_to_snake(self.__name__.removeprefix("Base"), delim=" ")

        return v


class BaseStructure(metaclass=_StructureMeta):
    # @property
    # def locked(self) -> _GeneratorContextManager[None]:
    #     return locked.equality_locked(self)

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
            return NotImplemented

        return self.__class__ is value.__class__ and self.identity == value.identity
