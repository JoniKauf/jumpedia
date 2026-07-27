from dataclasses import dataclass

from domain.entities.task import TaskEntity
from domain.typing.attribute import TaskAttributeTypeT
from domain.typing.field_mapping import FrozenFieldMappingEntityToStrings
from domain.typing.task import TaskID


@dataclass(frozen=True, slots=True)
class PreparedDeleteTask:
    task_id: TaskID


@dataclass(frozen=True, slots=True)
class TaskInfo:
    task: TaskEntity
    data: FrozenFieldMappingEntityToStrings[TaskAttributeTypeT]
