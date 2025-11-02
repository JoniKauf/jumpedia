import typing as t

from ...structures.attribute import BaseAttribute
from ...structures.attribute.slot_str import SlotType
from ...utils import text
from .. import BaseAdapter

if t.TYPE_CHECKING:
    from .._list import ListAdapter
    from .static_attribute import StaticAttributeAdapter
    from .task_attribute import TaskAttributeAdapter
    from .user_attribute import UserAttributeAdapter


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
    def _slot_type(self) -> SlotType:
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
