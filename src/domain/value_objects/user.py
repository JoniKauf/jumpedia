import typing as t

from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore

if t.TYPE_CHECKING:

    class UserName(StrStore):
        pass

else:
    UserName = factories.make_constrained_str_store_type(
        "UserName", CommunityLimits.USER_NAME_LENGTH_MAX, AttributeEntity
    )
