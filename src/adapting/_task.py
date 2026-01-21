import typing as t
from functools import cached_property

from adapting._user import CommunityUserAdapter
from structures.attribute.slot_str import SlotStr
from structures.task import Task
from structures.task.attribute_value_mapping import (
    AttributeValueMapping,
    UserAttributeValueMapping,
)
from structures.user import CommunityUser
from utils import orm

from . import BaseStructureAdapter

if t.TYPE_CHECKING:
    from ._list import ListAdapter


class TaskAdapter(BaseStructureAdapter[Task]):
    list: ListAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.list._c

    @property
    def name(self) -> SlotStr:
        return self._o.slot_name

    @t.overload
    def get_attribute_value_mapping(
        self, community_user: None = ..., /
    ) -> AttributeValueMapping:
        pass

    @t.overload
    def get_attribute_value_mapping(
        self, community_user: CommunityUserAdapter, /
    ) -> UserAttributeValueMapping:
        pass

    def get_attribute_value_mapping(
        self, community_user: CommunityUserAdapter | None = None, /
    ) -> AttributeValueMapping | UserAttributeValueMapping:
        return self._o.get_attribute_value_mapping(
            self._c, None if community_user is None else community_user._o.id
        )
