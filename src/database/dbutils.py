import enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Final
from database import strong as S
from database.strong import Tables as TBL, TableMeta

from structures.attribute import AnyAttributeT, StaticAttribute, TaskAttribute, UserAttribute

_ATTRIBUTE_TABLES: Final = (
    _ATTRIBUTE_TABLE := (TBL.StaticAttribute, TBL.TaskAttribute, TBL.UserAttribute),
    _ATTRIBUTE_ALIAS_TABLE := (TBL.StaticAttributeAlias, TBL.TaskAttributeAlias, TBL.UserAttributeAlias),
    _ATTRIBUTE_COLLECTION_NODE_TABLE := (None, TBL.TaskAttributeCollectionNode, TBL.UserAttributeCollectionNode),
    _ATTRIBUTE_COLLECTION_NODE_ALIAS_TABLE := (None, TBL.TaskAttributeCollectionNodeAlias, TBL.UserAttributeCollectionNodeAlias),
    _ATTRIBUTE_TASK_VALUE_TABLE := (TBL.StaticAttributeTaskValue, TBL.TaskAttributeTaskValue, TBL.UserAttributeTaskValue)
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

def get_attribute_task_value_table(attribute_type: type[AnyAttributeT]):
    return _ATTRIBUTE_TASK_VALUE_TABLE[_ATTRIBUTE_IDX.index(attribute_type)]