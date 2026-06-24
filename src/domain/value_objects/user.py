import typing as t

from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class UserName(Str):
        pass

else:
    UserName = factories.make_constrained_str_store_type(
        "UserName", CommunityLimits.USER_NAME_LENGTH_MAX, AttributeEntity
    )
