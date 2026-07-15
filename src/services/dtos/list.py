import typing as t
from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.list import ListNameStr
from domain.value_objects.string import Str
from repositories.attribute import AttributeEntity


@dataclass(frozen=True, slots=True)
class ListInfo:
    name: ListNameStr
    attributes: tuple[AttributeEntity, ...]
    task_count: int
    is_default_selected_list: bool


@dataclass(frozen=True, slots=True)
class ListSummary:
    name: ListNameStr
    attributes: tuple[AttributeEntity, ...]
    task_count: int
    is_default_selected_list: bool


@dataclass(frozen=True, slots=True)
class PreparedDeleteList:
    list_id: ListID
