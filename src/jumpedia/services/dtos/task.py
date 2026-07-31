from dataclasses import dataclass

from jumpedia.domain.entities.task import TaskEntity
from jumpedia.domain.typing.attribute import TaskAttributeTypeT
from jumpedia.domain.typing.field_mapping import FrozenFieldMappingEntityToStrings
from jumpedia.domain.typing.task import TaskID


@dataclass(frozen=True, slots=True)
class PreparedDeleteTask:
    task_id: TaskID


@dataclass(frozen=True, slots=True)
class TaskInfo:
    task: TaskEntity
    data: FrozenFieldMappingEntityToStrings[TaskAttributeTypeT]
