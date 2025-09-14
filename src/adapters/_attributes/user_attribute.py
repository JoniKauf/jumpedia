from dataclasses import dataclass

from adapters._base_adapter import BaseAdapter
from adapters._list import ListAdapter
from structures.attribute.user_attribute import UserAttribute


@dataclass(frozen=True)
class UserAttributeAdapter(BaseAdapter):
    _user_attribute: UserAttribute

    list: ListAdapter