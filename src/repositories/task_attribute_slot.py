

import typing as t
from db.models import TaskAttributeSlotModel
from domain.entities.task_attribute_slot import TaskAttributeSlotEntity
from domain.value_objects.index import Index
from domain.value_objects.task_attribute_slot import TaskAttributeSlot
from repositories.base import BaseRepository
from repositories.dtos.task_attribute_slot import TaskAttributeSlotInsert

def task_attribute_slot_model_to_entity(model: TaskAttributeSlotModel) -> TaskAttributeSlotEntity:
    return TaskAttributeSlotEntity(
        task_id=model.task_id,
        attribute_id=model.attribute_id,
        index=Index(model.index),
        slot=TaskAttributeSlot(
            _real=model.real_slot,
            _norm=model.norm_slot
        )
    )

class TaskAttributeSlotRepository(BaseRepository):
    def create_many(self, task_attribute_slots: t.Iterable[TaskAttributeSlotInsert]) -> list[TaskAttributeSlotEntity]:
        """Preserves order."""
        objs = tuple(
            TaskAttributeSlotModel(
                task_id=slot.task_id,
                attribute_id=slot.attribute_id,
                index=slot.index.value,
                norm_value=slot.slot.norm,
                real_value=slot.slot.real,
            )
            for slot in task_attribute_slots
        )

        self.session.add_all(objs)
        self.session.flush()

        return [task_attribute_slot_model_to_entity(obj) for obj in objs]
