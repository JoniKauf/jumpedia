import itertools
import types as ts
import typing as t

from certifi import where
from sqlalchemy import delete, select

from db.models import AttributeModel, MemberFieldSlotModel, MemberTaskModel
from domain.entities.member_field_slot import MemberFieldSlotEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.types.field_mapping import FieldMappingIDFrozenT
from domain.types.list import ListID
from domain.types.member import MemberID
from domain.types.member_task import MemberTaskID
from domain.types.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index
from repositories.base import BaseRepository
from repositories.dtos.member_field_slot import MemberFieldSlotInsert


class MemberFieldSlotRepository(BaseRepository):
    def create_many(
        self, member_field_slots: t.Iterable[MemberFieldSlotInsert]
    ) -> None:
        objs = tuple(
            MemberFieldSlotModel(
                member_task_id=slot.member_task_id,
                attribute_id=slot.attribute_id,
                index=slot.index.value,
                norm_slot=slot.slot.norm,
                real_slot=slot.slot.real,
            )
            for slot in member_field_slots
        )

        self._session.add_all(objs)
        self._session.flush()

    def get_field_mapping_by_member_id_and_task_id(
        self, member_id: MemberID, task_id: TaskID
    ) -> FieldMappingIDFrozenT:
        stmt = (
            select(MemberFieldSlotModel)
            .join(MemberTaskModel)
            .where(
                MemberTaskModel.member_id == member_id,
                MemberTaskModel.task_id == task_id,
            )
            .order_by(
                MemberFieldSlotModel.attribute_id.asc(),
                MemberFieldSlotModel.index.asc(),
            )
        )

        return frozendict(
            (k, tuple(FieldSlotStr._create(obj.real_slot, obj.norm_slot) for obj in g))
            for k, g in itertools.groupby(
                self._session.scalars(stmt), lambda obj: obj.attribute_id
            )
        )

    def get_grouped_member_field_mapping_by_list_id(
        self,
        list_id: ListID,
    ) -> frozendict[
        MemberTaskID,
        frozendict[AttributeID, tuple[FieldSlotStr, ...]],
    ]:
        stmt = (
            select(MemberFieldSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == MemberFieldSlotModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
            )
            .order_by(
                MemberFieldSlotModel.member_task_id.asc(),
                MemberFieldSlotModel.attribute_id.asc(),
                MemberFieldSlotModel.index.asc(),
            )
        )

        return frozendict(
            (
                task_id,
                frozendict(
                    (
                        attr_id,
                        tuple(
                            FieldSlotStr._create(obj.real_slot, obj.norm_slot)
                            for obj in attr_group
                        ),
                    )
                    for attr_id, attr_group in itertools.groupby(
                        task_group,
                        lambda obj: obj.attribute_id,
                    )
                ),
            )
            for task_id, task_group in itertools.groupby(
                self._session.scalars(stmt),
                lambda obj: obj.member_task_id,
            )
        )

    def replace_all_by_member_task_id(
        self,
        member_task_id: MemberTaskID,
        member_field_slots: t.Iterable[MemberFieldSlotInsert],
    ) -> None:
        stmt = delete(MemberFieldSlotModel).where(
            MemberFieldSlotModel.member_task_id == member_task_id
        )

        self._session.execute(stmt)
        self.create_many(member_field_slots)
