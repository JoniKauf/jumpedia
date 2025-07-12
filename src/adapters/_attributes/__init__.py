from typing import overload, assert_never
from adapters._attributes.static_attribute import StaticAttributeAdapter
from adapters._attributes.task_attribute import TaskAttributeAdapter
from adapters._attributes.user_attribute import UserAttributeAdapter
from adapters._list import ListAdapter
from structures import attributes
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute

type AnyAttributeAdapterT = StaticAttributeAdapter | TaskAttributeAdapter | UserAttributeAdapter