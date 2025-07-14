import enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Final
from database import layout
from structures.attributes import AnyAttributeT, CollectionAttributeT
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute

_ATTRIBUTE_TABLES: Final = (
    _ATTRIBUTE_TABLE := (layout.StaticAttribute, layout.TaskAttribute, layout.UserAttribute),
    _ATTRIBUTE_ALIAS_TABLE := (layout.StaticAttributeAlias, layout.TaskAttributeAlias, layout.UserAttributeAlias),
    _ATTRIBUTE_COLLECTION_NODE_TABLE := (None, layout.TaskAttributeCollectionNode, layout.UserAttributeCollectionNode),
    _ATTRIBUTE_COLLECTION_NODE_ALIAS_TABLE := (None, layout.TaskAttributeCollectionNodeAlias, layout.UserAttributeCollectionNodeAlias),
    _ATTRIBUTE_TASK_VALUE_TABLE := (layout.StaticAttributeTaskValue, layout.TaskAttributeTaskValue, layout.UserAttributeTaskValue)
)

_ATTRIBUTE_IDX = (StaticAttribute, TaskAttribute, UserAttribute)

class AttributeTableCategory(enum.Enum):
    ATTRIBUTE = 0
    ATTRIBUTE_ALIAS = 1
    ATTRIBUTE_COLLECTION_NODE = 2
    ATTRIBUTE_COLLECTION_NODE_ALIAS = 3
    ATTRIBUTE_TASK_VALUE = 4


class TableDoesNotExistException(LookupError):
    def __init__(self, attribute_type: type[AnyAttributeT], category: AttributeTableCategory | None = None, *args: object) -> None:
        self.attribute_type = attribute_type
        self.category = category

        super().__init__(*args)


def get_attribute_table(attribute_type: type[AnyAttributeT]):
    return _ATTRIBUTE_TABLE[_ATTRIBUTE_IDX.index(attribute_type)]

def get_attribute_alias_table(attribute_type: type[AnyAttributeT]):
    return _ATTRIBUTE_ALIAS_TABLE[_ATTRIBUTE_IDX.index(attribute_type)]

def get_attribute_task_value_table(attribute_type: type[AnyAttributeT]):
    return _ATTRIBUTE_TASK_VALUE_TABLE[_ATTRIBUTE_IDX.index(attribute_type)]

def get_attribute_collection_node_table(attribute_type: type[CollectionAttributeT]):
    result = _ATTRIBUTE_COLLECTION_NODE_TABLE[_ATTRIBUTE_IDX.index(attribute_type)]
    assert result is not None
    return result

def get_attribute_collection_node_alias_table(attribute_type: type[CollectionAttributeT]):
    result = _ATTRIBUTE_COLLECTION_NODE_ALIAS_TABLE[_ATTRIBUTE_IDX.index(attribute_type)]
    assert result is not None
    return result