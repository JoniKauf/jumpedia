import typing as t

from structures.attribute import BaseAttribute
from structures.attribute.slot_str import SlotTypeT
from structures.community import StaticAttribute
from structures.list import TaskAttribute, UserAttribute
from utils import text

from .. import BaseAdapter

if t.TYPE_CHECKING:
    from .._list import ListAdapter


class BaseAttributeAdapter[T: BaseAttribute](BaseAdapter):
    _attribute: T
    list: ListAdapter

    @property
    def id(self) -> int:
        return self._attribute.id

    @property
    def real_name(self) -> text.RealStr:
        return self._attribute.real_name

    @property
    def norm_name(self) -> text.NormStr:
        return self._attribute.norm_name

    @property
    def _slot_type(self) -> type[SlotTypeT]:
        return self._attribute.slot_type

    @property
    def position(self) -> int:
        return self._attribute.position

    @property
    def min_slots(self) -> int:
        return self._attribute.min_slots

    @property
    def max_slots(self) -> int:
        return self._attribute.max_slots


type AnyAttributeAdapterT = StaticAttributeAdapter | TaskAttributeAdapter | UserAttributeAdapter


class StaticAttributeAdapter(BaseAttributeAdapter[StaticAttribute]):
    @property
    def kind(self) -> int:
        return self._attribute.kind


class TaskAttributeAdapter(BaseAttributeAdapter[TaskAttribute]):
    pass


class UserAttributeAdapter(BaseAttributeAdapter[UserAttribute]):
    pass
