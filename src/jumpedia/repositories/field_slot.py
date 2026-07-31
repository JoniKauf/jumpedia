import typing as t

from sqlalchemy import delete, select

from jumpedia.db.models import AttributeModel, FieldSlotModel, TaskModel
from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.field_mapping import FrozenFieldMappingIDToStringsT
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.task import TaskID
from jumpedia.domain.value_objects.field_slot import FieldSlotStr, TaskEntity
from jumpedia.repositories.base import BaseRepository
from jumpedia.repositories.dtos.field_slot import FieldSlotInsert
from jumpedia.repositories.task import task_model_to_entity


class FieldSlotRepository(BaseRepository):
    def create_many(self, field_slots: t.Iterable[FieldSlotInsert]) -> None:
        """Preserves order."""
        objs = tuple(
            FieldSlotModel(
                task_id=slot.task_id,
                attribute_id=slot.attribute_id,
                index=slot.index.value,
                slot_hash=slot.slot.hash,
                slot=slot.slot.real,
            )
            for slot in field_slots
        )

        self._session.add_all(objs)
        self._session.flush()

    def replace_all_by_attribute_id(
        self,
        attribute_id: AttributeID,
        field_slots: t.Iterable[FieldSlotInsert],
    ) -> None:
        self._session.execute(
            delete(FieldSlotModel).where(FieldSlotModel.attribute_id == attribute_id)
        )

        self.create_many(field_slots)

    def replace_all_by_task_id(
        self,
        task_id: TaskID,
        field_slots: t.Iterable[FieldSlotInsert],
    ) -> None:
        self._session.execute(
            delete(FieldSlotModel).where(FieldSlotModel.task_id == task_id)
        )

        self.create_many(field_slots)

    def get_field_mapping_by_task_id(
        self, task_id: TaskID
    ) -> FrozenFieldMappingIDToStringsT:
        stmt = (
            select(FieldSlotModel)
            .where(FieldSlotModel.task_id == task_id)
            .order_by(
                FieldSlotModel.attribute_id.asc(),
                FieldSlotModel.index.asc(),
            )
        )

        res: dict[AttributeID, list[FieldSlotStr]] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.attribute_id, []).append(
                FieldSlotStr._create_from_real_and_hash(obj.slot, obj.slot_hash)
            )

        return frozendict({k: tuple(v) for k, v in res.items()})

    def get_task_field_mapping_by_list_id(
        self,
        list_id: ListID,
    ) -> frozendict[
        TaskID,
        FrozenFieldMappingIDToStringsT,
    ]:
        stmt = (
            select(FieldSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == FieldSlotModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
            )
            .order_by(
                FieldSlotModel.task_id.asc(),
                FieldSlotModel.attribute_id.asc(),
                FieldSlotModel.index.asc(),
            )
        )

        res: dict[
            TaskID,
            dict[AttributeID, list[FieldSlotStr]],
        ] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.task_id, {}).setdefault(obj.attribute_id, []).append(
                FieldSlotStr._create_from_real_and_hash(obj.slot, obj.slot_hash)
            )

        return frozendict(
            {
                task_id: frozendict(
                    {attr_id: tuple(slots) for attr_id, slots in attr_map.items()}
                )
                for task_id, attr_map in res.items()
            }
        )
