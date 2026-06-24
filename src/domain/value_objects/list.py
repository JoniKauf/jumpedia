import typing as t

from domain import errors
from domain.entities.list import ListEntity
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class ListName(Str):
        pass

else:
    ListName = factories.make_length_limited_str_store_type(
        "ListName", CommunityLimits.LIST_NAME_LENGTH_MAX, ListEntity
    )
