import typing as t

from jumpedia.domain.entities.task import TaskEntity
from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.value_objects import factories
from jumpedia.domain.value_objects.community import CommunityLimits

lazy from jumpedia.domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class FieldSlotStr(Str):
        """A string that holds the a single slot of a field. A field is a task's value for a specific attribute.

        It also represents the name and aliases of a task (and more), because in the same way,
        they are also technically just field slots logically. Read more about
        ~~static attributes~~ attribute kinds for more info.
        """

else:
    FieldSlotStr = factories.make_length_limited_str_store_type(
        "FieldSlotStr",
        CommunityLimits.FIELD_SLOT_LENGTH_MAX,
        Concept.FIELD_SLOT,
    )
