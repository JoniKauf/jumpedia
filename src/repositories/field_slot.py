import types as ts
import typing as t

from sqlalchemy import select

from db.models import AttributeModel, FieldSlotModel, TaskModel
from domain.entities.field_slot import FieldSlotEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr, TaskEntity
from domain.value_objects.index import Index
from repositories.base import BaseRepository
from repositories.dtos.field_slot import FieldSlotInsert
from repositories.task import task_model_to_entity


def field_slot_model_to_entity(
    model: FieldSlotModel,
) -> FieldSlotEntity:
    return FieldSlotEntity(
        task_id=model.task_id,
        attribute_id=model.attribute_id,
        index=Index(model.index),
        slot=FieldSlotStr(_real=model.real_slot, _norm=model.norm_slot),
    )


class FieldSlotRepository(BaseRepository):
    def create_many(
        self, field_slots: t.Iterable[FieldSlotInsert]
    ) -> tuple[FieldSlotEntity, ...]:
        """Preserves order."""
        objs = tuple(
            FieldSlotModel(
                task_id=slot.task_id,
                attribute_id=slot.attribute_id,
                index=slot.index.value,
                norm_value=slot.slot.norm,
                real_value=slot.slot.real,
            )
            for slot in field_slots
        )

        self._session.add_all(objs)
        self._session.flush()

        return tuple(field_slot_model_to_entity(obj) for obj in objs)

    def get_field_mapping_by_task_id(
        self, task_id: TaskID, types: t.AbstractSet[AttributeType]
    ) -> ts.MappingProxyType[AttributeID, tuple[FieldSlotEntity, ...]]:
        stmt = (
            select(FieldSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == FieldSlotModel.attribute_id,
            )
            .where(
                FieldSlotModel.task_id == task_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                FieldSlotModel.attribute_id.asc(),
                FieldSlotModel.index.asc(),
            )
        )

        res: dict[AttributeID, list[FieldSlotEntity]] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.attribute_id, []).append(field_slot_model_to_entity(obj))

        return ts.MappingProxyType({k: tuple(v) for k, v in res.items()})

    def get_field_mapping_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
    ) -> ts.MappingProxyType[
        TaskID,
        ts.MappingProxyType[AttributeID, tuple[FieldSlotEntity, ...]],
    ]:
        stmt = (
            select(FieldSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == FieldSlotModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                FieldSlotModel.task_id.asc(),
                FieldSlotModel.attribute_id.asc(),
                FieldSlotModel.index.asc(),
            )
        )

        res: dict[
            TaskID,
            dict[AttributeID, list[FieldSlotEntity]],
        ] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.task_id, {}).setdefault(obj.attribute_id, []).append(
                field_slot_model_to_entity(obj)
            )

        return ts.MappingProxyType(
            {
                task_id: ts.MappingProxyType(
                    {attr_id: tuple(slots) for attr_id, slots in attr_map.items()}
                )
                for task_id, attr_map in res.items()
            }
        )

    def get_grouped_by_task(
        self,
        attribute_id: AttributeID,
    ) -> ts.MappingProxyType[TaskEntity, tuple[FieldSlotStr, ...]]:
        stmt = (
            select(TaskModel, FieldSlotModel)
            .join(
                FieldSlotModel,
                FieldSlotModel.task_id == TaskModel.task_id,
            )
            .where(FieldSlotModel.attribute_id == attribute_id)
            .order_by(
                TaskModel.task_id.asc(),
                FieldSlotModel.index.asc(),
            )
        )

        tasks: dict[TaskID, TaskEntity] = {}
        res: dict[TaskEntity, list[FieldSlotStr]] = {}

        for task_obj, slot_obj in self._session.execute(stmt):
            task_obj: TaskModel
            slot_obj: FieldSlotModel

            task = tasks.get(task_obj.task_id)

            if task is None:
                task = task_model_to_entity(task_obj)
                tasks[task_obj.task_id] = task
                res[task] = []

            res[task].append(
                FieldSlotStr(
                    _real=slot_obj.real_slot,
                    _norm=slot_obj.norm_slot,
                )
            )

        return ts.MappingProxyType({task: tuple(slots) for task, slots in res.items()})
