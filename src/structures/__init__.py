

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from structures.abstract_structure import AbstractStructure
from utils import text

_cls_names: dict[str, type['AbstractStructure']] = {}

def get_structure_classes() -> tuple[type['AbstractStructure'], ...]:
    return tuple(_cls_names.values())
