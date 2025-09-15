from adapters import BaseAdapter
from adapters._list import ListAdapter
from structures.attribute.user_attribute import UserAttribute

class UserAttributeAdapter(BaseAdapter):
    _user_attribute: UserAttribute

    list: ListAdapter