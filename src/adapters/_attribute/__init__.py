from adapters import BaseAdapter
from adapters._attribute.static_attribute import StaticAttributeAdapter
from adapters._attribute.task_attribute import TaskAttributeAdapter
from adapters._attribute.user_attribute import UserAttributeAdapter
from adapters._list import ListAdapter
from structures.attribute import BaseAttribute
from structures.attribute.slot_type import SlotType, SlotTypeT
from utils import text


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