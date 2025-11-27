import typing as t

from adapters._user import CommunityUserAdapter
from structures.attribute.slot_str import SlotStr
from structures.task import Task
from structures.task.attribute_value_mapping import AttributeValueMapping, UserAttributeValueMapping
from structures.user import CommunityUser

from . import BaseStructureAdapter

if t.TYPE_CHECKING:
    from ._list import ListAdapter


class TaskAdapter(BaseStructureAdapter[Task]):
    list: ListAdapter

    @property
    def name(self) -> SlotStr:
        return self._s.slot_name
    
    @t.overload
    def get_attribute_value_mapping(self, community_user: None = ..., /) -> AttributeValueMapping:
        pass

    @t.overload
    def get_attribute_value_mapping(self, community_user: CommunityUserAdapter, /) -> UserAttributeValueMapping:
        pass

    def get_attribute_value_mapping(self, community_user: CommunityUserAdapter | None = None, /) -> AttributeValueMapping | UserAttributeValueMapping:
        return self._s.get_attribute_value_mapping(None if community_user is None else community_user._s.id)
