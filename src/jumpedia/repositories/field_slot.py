import itertools
import typing as t
from operator import itemgetter

from sqlalchemy import delete, select

from jumpedia.db.models import AttributeModel, FieldSlotModel
from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.field_mapping import FrozenFieldMappingIDToStringsT
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.task import TaskID
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.repositories.base import BaseRepository
from jumpedia.repositories.dtos.field_slot import FieldSlotInsert


class FieldSlotRepository(BaseRepository):
    def create_many(self, field_slots: t.Iterable[FieldSlotInsert]) -> None:
        """Preserves order."""
        objs = tuple(
            FieldSlotModel(
                list_id=slot.list_id,
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
        # For task browse (the most expensive operation) this function is the bottleneck
        # It is optimized as much as possible for speed and not for clarity

        stmt = (
            select(
                FieldSlotModel.task_id,
                FieldSlotModel.attribute_id,
                FieldSlotModel.slot,
                FieldSlotModel.slot_hash,
            )
            .where(FieldSlotModel.list_id == list_id)
            .order_by(
                FieldSlotModel.task_id,
                FieldSlotModel.attribute_id,
                FieldSlotModel.index,
            )
        )

        create = FieldSlotStr._create_from_real_and_hash
        get_task_id = itemgetter(0)
        get_attr_id = itemgetter(1)

        res: dict[TaskID, FrozenFieldMappingIDToStringsT] = {}

        for task_id, task_group in itertools.groupby(
            self._session.execute(stmt).tuples(),
            key=get_task_id,
        ):
            attr_map: dict[AttributeID, tuple[FieldSlotStr, ...]] = {}

            for attr_id, attr_group in itertools.groupby(
                task_group,
                key=get_attr_id,
            ):
                attr_map[attr_id] = tuple(
                    create(slot, slot_hash) for _, _, slot, slot_hash in attr_group
                )

            res[task_id] = frozendict(attr_map)

        return frozendict(res)
