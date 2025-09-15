from adapters import BaseAdapter
from adapters._list import ListAdapter
from structures.attribute.static_attribute import StaticAttribute

class StaticAttributeAdapter(BaseAdapter):
    _static_attribute: StaticAttribute

    list: ListAdapter