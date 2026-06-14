from dataclasses import dataclass
import typing as t

from domain.types.id import ID
from domain.value_objects.list import ListName
from domain.value_objects.string import StrStore
from repositories.attribute import AttributeEntity


@dataclass(frozen=True, slots=True)
class ListInfoDTO:
    name: ListName
    attributes: tuple[AttributeEntity, ...]
    task_count: int
    is_default_selected_list: bool

@dataclass(frozen=True, slots=True)
class ListSummaryDTO:
    name: ListName
    attributes: tuple[AttributeEntity, ...]
    task_count: int
    is_default_selected_list: bool

@dataclass(frozen=True, slots=True)
class DeletedListDTO:
    community_id: ID
    name: ListName