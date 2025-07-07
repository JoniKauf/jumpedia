from dataclasses import dataclass

from adapters._base_adapter import BaseAdapter
from adapters._list._list import ListAdapter
from structures.attributes.static_attribute import StaticAttribute


@dataclass(frozen=True)
class StaticAttributeAdapter(BaseAdapter):
    _static_attribute: StaticAttribute

    list: ListAdapter