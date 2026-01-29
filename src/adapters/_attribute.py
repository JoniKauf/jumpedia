import typing as t
from functools import cached_property

from structures.attribute import BaseAttribute
from structures.attribute.slot_str import SlotTypeT
from structures.community import StaticAttribute
from structures.list import TaskAttribute, UserAttribute
from utils import orm, text

from . import BaseStructureAdapter

if t.TYPE_CHECKING:
    from ._list import ListAdapter


class BaseAttributeAdapter[T: BaseAttribute](BaseStructureAdapter[T]):
    list: ListAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.list._c

    @property
    def slot_type(self) -> type[SlotTypeT]:
        return self._o.slot_type

    @property
    def position(self) -> int:
        return self._o.position

    @property
    def min_slot_count(self) -> int:
        return self._o.min_slot_count

    @property
    def max_slot_count(self) -> int:
        return self._o.max_slot_count


type AnyAttributeAdapterT = StaticAttributeAdapter | TaskAttributeAdapter | UserAttributeAdapter


class StaticAttributeAdapter(BaseAttributeAdapter[StaticAttribute]):
    @property
    def kind(self) -> int:
        return self._o.kind


class TaskAttributeAdapter(BaseAttributeAdapter[TaskAttribute]):
    pass


class UserAttributeAdapter(BaseAttributeAdapter[UserAttribute]):
    pass
