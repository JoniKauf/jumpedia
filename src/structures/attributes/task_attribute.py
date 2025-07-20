
from dataclasses import dataclass
from database import typed
from structures.attributes import SlotTypeT, Uniqueness
from structures.attributes.collection import CollectionAttributeTables, BaseCollectionAttribute


@dataclass(frozen=True, kw_only=True)
class TaskAttribute[T: SlotTypeT](BaseCollectionAttribute[T]):
    __structure_name__ = 'task attribute'
    tables = CollectionAttributeTables(
        typed.TaskAttribute,
        typed.TaskAttributeAlias,
        typed.TaskAttributeTaskValue,
        typed.TaskAttributeCollectionNode,
        typed.TaskAttributeCollectionNodeAlias
    )