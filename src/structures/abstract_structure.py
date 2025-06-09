
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, final

import structures
from utils import text


@dataclass(frozen=True, kw_only=True)
class AbstractStructure(ABC):
    __structure_name__: ClassVar[str] = ""

    @property
    @abstractmethod
    def identity(self) -> tuple[int, ...]:
        """Uniquely identify an object of this type."""
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, AbstractStructure):
            print(f"Compared", value, "to", self)
            return False
        
        return self.__class__ != value.__class__ and self.identity == value.identity
    
    @property
    @abstractmethod
    def parent(self) -> 'AbstractStructure':
        ...

    def __init_subclass__(cls) -> None:
        structure_name = text.norm(cls.__structure_name__)

        if structure_name in structures._cls_names:
            raise AssertionError("__structure_name__ used twice")
        
        structures._cls_names[structure_name] = cls

        return super().__init_subclass__()