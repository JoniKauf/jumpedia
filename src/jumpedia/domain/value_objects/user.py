import typing as t

from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.value_objects.community import CommunityLimits

lazy from jumpedia.domain.value_objects.string import Str
from jumpedia.domain.entities.attribute import AttributeEntity
from jumpedia.domain.value_objects import factories

if t.TYPE_CHECKING:

    class UserNameStr(Str):
        pass

else:
    UserNameStr = factories.make_length_limited_str_store_type(
        "UserNameStr", CommunityLimits.USER_NAME_LENGTH_MAX, Concept.USER
    )
