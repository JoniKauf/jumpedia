import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property

from utils import orm, text

type StructuresTypeT = type[BaseStructure] | tuple[
    type[BaseStructure], *tuple[type[BaseStructure], ...]
]


_cls_to_naming: t.Final[dict[str, tuple[str, str]]] = {}


@t.dataclass_transform(frozen_default=True, kw_only_default=True, eq_default=False)
class _StructureMeta(ABCMeta):
    """Metaclass of all structures.

    It combines ABC and dataclass behaviour with fully supported typing.
    """

    type_name: str
    type_name_plural: str

    if t.TYPE_CHECKING:

        def __new__(
            mcls: type[_StructureMeta],
            name: str,
            bases: tuple[type, ...],
            namespace: dict[str, t.Any],
            *,
            naming: tuple[str, str],
        ) -> _StructureMeta: ...

    else:

        def __new__(
            mcls: type[_StructureMeta],
            name: str,
            bases: tuple[type, ...],
            namespace: dict[str, t.Any],
            *,
            naming: tuple[str, str] = None,  # type: ignore
        ) -> _StructureMeta:
            cls = super().__new__(mcls, name, bases, namespace)

            # First we go in here, then dataclass calls this function again without naming, so we pass by here the second time
            if namespace.get("__dataclass_fields__") is None:
                _cls_to_naming[cls.__qualname__] = naming
                return dataclass(frozen=True, slots=True, kw_only=True, eq=False)(cls)  # type: ignore

            cls.type_name, cls.type_name_plural = _cls_to_naming[cls.__qualname__]

            return cls  # type: ignore

    def __str__(self) -> str:
        return self.type_name


class BaseStructure(metaclass=_StructureMeta, naming=("structure", "structures")):
    id: int

    @property
    @abstractmethod
    def name(self) -> str: ...

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, value: object) -> bool:
        return self.__class__ is value.__class__ and self.id == value.id  # type: ignore

    def __str__(self) -> str:
        return self.name


class BaseStructureWithAliases(BaseStructure, naming=("structure", "structures")):
    @abstractmethod
    def get_aliases(self, c: orm.Cursor, /) -> frozenset[str]: ...
