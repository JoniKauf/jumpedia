from dataclasses import dataclass
import typing as t

from domain.value_objects.strings import StrStore
from repositories.attribute import AttributeEntity

@dataclass(frozen=True, slots=True)
class ListInfo:
    name: StrStore
    attributes: tuple[AttributeEntity, ...]
    task_count: int
    is_default_selected_list: bool