import typing as t
from dataclasses import dataclass

from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.value_objects.list import ListNameStr
from jumpedia.domain.value_objects.string import Str
from jumpedia.repositories.attribute import AttributeEntity


@dataclass(frozen=True, slots=True)
class ListInfo:
    list: ListEntity
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
