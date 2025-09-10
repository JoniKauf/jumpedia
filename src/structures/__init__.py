
from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, ClassVar, dataclass_transform
from contextlib import _GeneratorContextManager
import structures
from utils import text
from utils import locked


type StructuresTypeT = type[BaseStructure] | tuple[type[BaseStructure], *tuple[type[BaseStructure], ...]]

_cls_names: dict[str, type['BaseStructure']] = {}

def get_structure_types() -> tuple[type['BaseStructure'], ...]:
    return tuple(_cls_names.values())

def human_join_structures_type(structures: StructuresTypeT, convert: Callable[[str], str] = lambda s: s):
    if not isinstance(structures, tuple):
        structures = (structures,)
    
    return text.human_join(tuple(
        convert(s.__structure_name__) for s in structures
    ), " or ")


@dataclass_transform(frozen_default=True, kw_only_default=True)
class _StructureMeta(ABCMeta):
    """Metaclass of all structures.

    It combines ABC and dataclass(frozen=True, kw_only=True) behaviour,
    with support for typing.
    """
    def __new__(mcls: type[_StructureMeta], name: str, bases: tuple[type, ...], namespace: dict[str, Any], /, **kwargs: Any) -> _StructureMeta:
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        return dataclass(frozen=True, kw_only=True)(cls)  # type: ignore


class BaseStructure(metaclass=_StructureMeta):
    __structure_name__: ClassVar[str] = ''

    @property
    @abstractmethod
    def identity(self) -> tuple[int, ...]:
        """Uniquely identify an object of this type."""
    
    @property
    def locked(self) -> _GeneratorContextManager[RLock, None, None]:
        return locked.equality_locked(self)
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, BaseStructure):
            print(f"Compared", value, "to", self)
            return NotImplemented
        
        return self.__class__ == value.__class__ and self.identity == value.identity

    def __init_subclass__(cls) -> None:
        structure_name = text.norm_value(cls.__structure_name__)

        if structure_name in structures._cls_names:
            raise AssertionError("__structure_name__ used twice")
        
        structures._cls_names[structure_name] = cls

        return super().__init_subclass__()

    @classmethod
    def structure_name(cls, title: bool = False) -> str:
        if title:
            return cls.__structure_name__.title()
        else:
            return cls.__structure_name__.lower()