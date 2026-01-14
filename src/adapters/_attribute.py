import typing as t

from structures.attribute import BaseAttribute
from structures.attribute.slot_str import SlotTypeT
from structures.community import StaticAttribute
from structures.list import TaskAttribute, UserAttribute
from utils import orm, text

from . import BaseAdapter

if t.TYPE_CHECKING:
    from ._list import ListAdapter


class AttributeAdapter[T: BaseAttribute](BaseAdapter[T]):
    list: ListAdapter

    @property
    def _c(self) -> orm.Cursor:
        return self.list._c

    @property
    def id(self) -> int:
        return self._o.id

    @property
    def name(self) -> text.RealStr:
        return self._o.real_name

    @property
    def slot_type(self) -> type[SlotTypeT]:
        return self._o.slot_type

    @property
    def position(self) -> int:
        return self._o.position

    @property
    def min_slots(self) -> int:
        return self._o.min_slots

    @property
    def max_slots(self) -> int:
        return self._o.max_slots


type AnyAttributeAdapterT = StaticAttributeAdapter | TaskAttributeAdapter | UserAttributeAdapter


class StaticAttributeAdapter(AttributeAdapter[StaticAttribute]):
    @property
    def kind(self) -> int:
        return self._o.kind


class TaskAttributeAdapter(AttributeAdapter[TaskAttribute]):
    pass


class UserAttributeAdapter(AttributeAdapter[UserAttribute]):
    pass
