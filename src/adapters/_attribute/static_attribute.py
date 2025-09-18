from adapters import BaseAdapter
from adapters._attribute import BaseAttributeAdapter
from adapters._list import ListAdapter
from structures.attribute.slot_type import SlotType, SlotTypeT
from structures.attribute.static_attribute import StaticAttribute

class StaticAttributeAdapter(BaseAttributeAdapter[StaticAttribute]):    
    @property
    def kind(self) -> int:
        return self._attribute.kind