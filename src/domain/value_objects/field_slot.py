import typing as t

from domain.entities.task import TaskEntity
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class FieldSlotStr(Str):
        """A string that holds the a single slot of a field. A field is a value for a specific task's attribute.

        It also represents the name and aliases of a task, because in the same way,
        they are also technically just field slots logically. Read more about
        static attributes for more info.
        """

else:
    FieldSlotStr = factories.make_length_limited_str_store_type(
        "FieldSlotStr",
        CommunityLimits.FIELD_SLOT_LENGTH_MAX,
        TaskEntity,
    )