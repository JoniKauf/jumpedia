
from dataclasses import dataclass
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.task.abstract_attribute_value_mapping import AbstractAttributeValueMapping


type TaskAttributeValueMappingAttributeT = StaticAttribute | TaskAttribute


@dataclass(frozen=True, kw_only=True)
class TaskAttributeValueMapping(AbstractAttributeValueMapping[TaskAttributeValueMappingAttributeT]):
    """Task Attribute Value Collection"""