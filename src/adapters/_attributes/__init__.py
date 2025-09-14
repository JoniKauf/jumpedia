from typing import overload, assert_never
from adapters._attributes.static_attribute import StaticAttributeAdapter
from adapters._attributes.task_attribute import TaskAttributeAdapter
from adapters._attributes.user_attribute import UserAttributeAdapter
from adapters._list import ListAdapter
from structures import attribute
from structures.attribute.static_attribute import StaticAttribute
from structures.attribute.task_attribute import TaskAttribute
from structures.attribute.user_attribute import UserAttribute

type AnyAttributeAdapterT = StaticAttributeAdapter | TaskAttributeAdapter | UserAttributeAdapter