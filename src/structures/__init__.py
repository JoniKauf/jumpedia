

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, ClassVar

from errors.feedback import FeedbackError
from structures.base_structure import BaseStructure
from utils import text
from discordtools import messaging as msg

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

def name_not_end_in_structure_name(name: str, structure: BaseStructure) -> None:
    if text.norm(name).endswith(text.norm(structure.structure_name())):
        return FeedbackError(
            f"Name Ends In {structure.structure_name(True)}",
            f"The name of the specified {structure.structure_name()} ends in {msg.code(name)}!",
            additional="Please leave that part out of the name, as it is redundant and would make feedback messages more confusing to understand."
        )