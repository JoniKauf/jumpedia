import typing as t

from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class UserNameStr(Str):
        pass

else:
    UserNameStr = factories.make_constrained_str_store_type(
        "UserNameStr", CommunityLimits.USER_NAME_LENGTH_MAX, AttributeEntity
    )
