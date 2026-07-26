import typing as t

from domain.enums.concept import Concept
from domain.value_objects.community import CommunityLimits

lazy from domain.value_objects.string import Str
from domain.entities.attribute import AttributeEntity
from domain.value_objects import factories

if t.TYPE_CHECKING:

    class UserNameStr(Str):
        pass

else:
    UserNameStr = factories.make_length_limited_str_store_type(
        "UserNameStr", CommunityLimits.USER_NAME_LENGTH_MAX, Concept.USER
    )
