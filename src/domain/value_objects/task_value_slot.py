import typing as t

from domain.entities.task import TaskEntity
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str


if t.TYPE_CHECKING:

    class TaskValueSlot(Str):
        pass

else:
    TaskValueSlot = factories.make_length_limited_str_store_type(
        "TaskValueSlot", CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX, TaskEntity
    )