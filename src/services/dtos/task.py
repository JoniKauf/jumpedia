import types as ts
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeType
from domain.types.task import TaskID
from domain.types.user import UserID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.user import UserNameStr


@dataclass(frozen=True, slots=True)
class DeletedTask:
    name: FieldSlotStr
    list: ListEntity


@dataclass(frozen=True, slots=True)
class TaskInfo:
    id: TaskID
    name: FieldSlotStr
    aliases: tuple[FieldSlotStr, ...]
    list: ListEntity
    field_mapping: frozendict[AttributeEntity.OfTypeTaskT, tuple[FieldSlotStr, ...]]
    static_attributes: tuple[
        AttributeEntity.OfTypeStaticT,
        AttributeEntity.OfTypeStaticT,
        AttributeEntity.OfTypeStaticT,
    ]