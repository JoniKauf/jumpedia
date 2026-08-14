import typing as t

from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.value_objects import factories
from jumpedia.domain.value_objects.community import CommunityLimits

lazy from jumpedia.domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class ListNameStr(Str):
        pass

else:
    ListNameStr = factories.make_length_limited_str_store_type(
        "ListNameStr", CommunityLimits.LIST_NAME_LENGTH_MAX, Concept.LIST
    )
