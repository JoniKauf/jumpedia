import types as ts
import typing as t

from sqlalchemy import select

from db.models import AttributeModel, TaskAttributeSlotModel, TaskModel
from domain.entities.task_attribute_slot import TaskAttributeSlotEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.index import Index
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr
from repositories.base import BaseRepository
from repositories.dtos.task_attribute_slot import TaskAttributeSlotInsert


def task_attribute_slot_model_to_entity(
    model: TaskAttributeSlotModel,
) -> TaskAttributeSlotEntity:
    return TaskAttributeSlotEntity(
        task_id=model.task_id,
        attribute_id=model.attribute_id,
        index=Index(model.index),
        slot=TaskAttributeSlotStr(_real=model.real_slot, _norm=model.norm_slot),
    )


class TaskAttributeSlotRepository(BaseRepository):
    def create_many(
        self, task_attribute_slots: t.Iterable[TaskAttributeSlotInsert]
    ) -> tuple[TaskAttributeSlotEntity, ...]:
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

        self._session.add_all(objs)
        self._session.flush()

        return tuple(task_attribute_slot_model_to_entity(obj) for obj in objs)

    def get_attribute_value_mapping_by_task_id(
        self, task_id: TaskID, types: t.AbstractSet[AttributeType]
    ) -> ts.MappingProxyType[AttributeID, tuple[TaskAttributeSlotEntity, ...]]:
        stmt = (
            select(TaskAttributeSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == TaskAttributeSlotModel.attribute_id,
            )
            .where(
                TaskAttributeSlotModel.task_id == task_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                TaskAttributeSlotModel.attribute_id.asc(),
                TaskAttributeSlotModel.index.asc(),
            )
        )

        res: dict[AttributeID, list[TaskAttributeSlotEntity]] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.attribute_id, []).append(
                task_attribute_slot_model_to_entity(obj)
            )

        return ts.MappingProxyType({k: tuple(v) for k, v in res.items()})

    def get_attribute_value_mapping_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
    ) -> ts.MappingProxyType[
        TaskID,
        ts.MappingProxyType[AttributeID, tuple[TaskAttributeSlotEntity, ...]],
    ]:
        stmt = (
            select(TaskAttributeSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == TaskAttributeSlotModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                TaskAttributeSlotModel.task_id.asc(),
                TaskAttributeSlotModel.attribute_id.asc(),
                TaskAttributeSlotModel.index.asc(),
            )
        )

        res: dict[
            TaskID,
            dict[AttributeID, list[TaskAttributeSlotEntity]],
        ] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.task_id, {}).setdefault(obj.attribute_id, []).append(
                task_attribute_slot_model_to_entity(obj)
            )

        return ts.MappingProxyType(
            {
                task_id: ts.MappingProxyType(
                    {attr_id: tuple(slots) for attr_id, slots in attr_map.items()}
                )
                for task_id, attr_map in res.items()
            }
        )
