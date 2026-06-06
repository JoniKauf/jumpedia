from dataclasses import dataclass
import typing as t

from domain.value_objects.list import ListName
from domain.value_objects.string import StrStore
from repositories.attribute import AttributeEntity


@dataclass(frozen=True, slots=True)
class ListInfoDTO:
    name: ListName
    attributes: tuple[AttributeEntity, ...]
    task_count: int
    is_default_selected_list: bool
