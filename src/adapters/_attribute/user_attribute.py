from adapters import BaseAdapter
from adapters._attribute import BaseAttributeAdapter
from adapters._list import ListAdapter
from structures.attribute.slot_type import SlotType, SlotTypeT
from structures.attribute.user_attribute import UserAttribute

class UserAttributeAdapter(BaseAttributeAdapter[UserAttribute]):
    pass