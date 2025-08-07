"""The internal structures Jumpedia works with behind the scenes.

All structures must follow these idioms:
- All structures have a parent, besides Jumpedia, which is the root.
- All structures are managed by their parent, which includes retrieval, 
  creation, deletion and editing.
- The parent must be locked when any state of the child will be changed. This
  also includes retrieval of data before editing the data, otherwise the data
  could become outdated by the time it is used.
- Structures are passed to other structures by ids if required. This is
  because the database could have been updated by then.
- Names and values of structures are compared by equality from the database.
- Dynamic data is compared by the code via normalization.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import enum
import functools
from typing import Any, Callable, ClassVar, ParamSpec

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