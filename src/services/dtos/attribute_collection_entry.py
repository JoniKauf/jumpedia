from dataclasses import dataclass

from domain.value_objects.task_attribute_slot import TaskAttributeSlot


@dataclass(frozen=True, slots=True)
class CreateAttributeCollectionEntry:
    value: TaskAttributeSlot
    aliases: tuple[TaskAttributeSlot, ...]
