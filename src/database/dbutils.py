import enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Final
from database import typed as typed
from database.typed import Tables as Tables, TableMeta
from structures.attributes import AnyAttributeT, CollectionAttributeT
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute

_ATTRIBUTE_TABLES: Final = (
    _ATTRIBUTE_TABLE := (Tables.StaticAttribute, Tables.TaskAttribute, Tables.UserAttribute),
    _ATTRIBUTE_ALIAS_TABLE := (Tables.StaticAttributeAlias, Tables.TaskAttributeAlias, Tables.UserAttributeAlias),
    _ATTRIBUTE_COLLECTION_NODE_TABLE := (None, Tables.TaskAttributeCollectionNode, Tables.UserAttributeCollectionNode),
    _ATTRIBUTE_COLLECTION_NODE_ALIAS_TABLE := (None, Tables.TaskAttributeCollectionNodeAlias, Tables.UserAttributeCollectionNodeAlias),
    _ATTRIBUTE_TASK_VALUE_TABLE := (Tables.StaticAttributeTaskValue, Tables.TaskAttributeTaskValue, Tables.UserAttributeTaskValue)
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