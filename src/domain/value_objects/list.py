import typing as t

from domain.entities.list import ListEntity
from domain.errors import business
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class ListNameStr(Str):
        pass

else:
    ListNameStr = factories.make_length_limited_str_store_type(
        "ListNameStr", CommunityLimits.LIST_NAME_LENGTH_MAX, ListEntity
    )
