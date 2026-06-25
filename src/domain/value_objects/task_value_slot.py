import typing as t

from domain.entities.task import TaskEntity
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str


if t.TYPE_CHECKING:

    class TaskValueSlot(Str):
        """A string that holds a slot's value of a task attribute value.
        
        It also represents the name and aliases of an attribute, because in the same way,
        they are also technically just attribute value slots.
        """

else:
    TaskValueSlot = factories.make_length_limited_str_store_type(
        "TaskValueSlot", CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX, TaskEntity
    )

