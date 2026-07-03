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
    field_mapping: ts.MappingProxyType[AttributeEntity.TaskT, tuple[FieldSlotStr, ...]]
    static_attributes: tuple[
        AttributeEntity.StaticT, AttributeEntity.StaticT, AttributeEntity.StaticT
    ]


@dataclass(frozen=True, slots=True)
class TaskSummary:
    id: TaskID
    name: FieldSlotStr
    aliases: tuple[FieldSlotStr, ...]
    list: ListEntity
    field_mapping: ts.MappingProxyType[AttributeEntity.TaskT, tuple[FieldSlotStr, ...]]


@dataclass(frozen=True, slots=True)
class TaskSummariesData:
    summaries: tuple[TaskSummary, ...]
    static_attributes: AttributeEntity.AllStaticT
    task_attributes: tuple[AttributeEntity.TaskT, ...]


@dataclass(frozen=True, slots=True)
class UserRef:
    id: UserID
    name: UserNameStr
