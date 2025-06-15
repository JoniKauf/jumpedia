
from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import RLock
from typing import ClassVar, final
from contextlib import _GeneratorContextManager
import structures
from utils import text
from utils.locked import equality_locked


@dataclass(frozen=True, kw_only=True)
class BaseStructure(ABC):
    __structure_name__: ClassVar[str] = ''

    @property
    @abstractmethod
    def identity(self) -> tuple[int, ...]:
        """Uniquely identify an object of this type."""
    
    @property
    def locked(self) -> _GeneratorContextManager[RLock, None, None]:
        return equality_locked(self)
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, BaseStructure):
            print(f"Compared", value, "to", self)
            return False
        
        return self.__class__ != value.__class__ and self.identity == value.identity

    def __init_subclass__(cls) -> None:
        structure_name = text.norm(cls.__structure_name__)

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