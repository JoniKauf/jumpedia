

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, ClassVar

from structures.abstract_structure import StructureBase
from utils import text

_cls_names: dict[str, type['StructureBase']] = {}

def get_structure_types() -> tuple[type['StructureBase'], ...]:
    return tuple(_cls_names.values())

type StructuresTypeT = type[StructureBase] | tuple[type[StructureBase], *tuple[type[StructureBase], ...]]

def human_join_structures_type(structures: StructuresTypeT, convert: Callable[[str], str] = lambda s: s):
    if not isinstance(structures, tuple):
        structures = (structures,)
    
    return text.human_join(tuple(
        convert(s.__structure_name__) for s in structures
    ), " or ")