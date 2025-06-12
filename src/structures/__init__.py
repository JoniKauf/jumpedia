

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, ClassVar

from structures.base_structure import BaseStructure
from utils import text

_cls_names: dict[str, type['BaseStructure']] = {}

def get_structure_types() -> tuple[type['BaseStructure'], ...]:
    return tuple(_cls_names.values())

type StructuresTypeT = type[BaseStructure] | tuple[type[BaseStructure], *tuple[type[BaseStructure], ...]]

def human_join_structures_type(structures: StructuresTypeT, convert: Callable[[str], str] = lambda s: s):
    if not isinstance(structures, tuple):
        structures = (structures,)
    
    return text.human_join(tuple(
        convert(s.__structure_name__) for s in structures
    ), " or ")