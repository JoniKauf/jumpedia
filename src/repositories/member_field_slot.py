import itertools
import typing as t

from sqlalchemy import delete, select

from db.models import MemberFieldSlotModel, MemberTaskModel
from domain.typing.attribute import AttributeID
from domain.typing.field_mapping import FrozenFieldMappingIDToStringsT
from domain.typing.member import MemberID
from domain.typing.member_task import MemberTaskID
from domain.typing.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr
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
                slot=slot.slot.real,
                slot_hash=slot.slot.hash,
            )
            for slot in member_field_slots
        )

        self._session.add_all(objs)
        self._session.flush()

    def get_field_mapping_by_member_id_and_task_id(
        self, member_id: MemberID, task_id: TaskID
    ) -> FrozenFieldMappingIDToStringsT:
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
            (
                k,
                tuple(
                    FieldSlotStr._create_from_real_and_hash(obj.slot, obj.slot_hash)
                    for obj in g
                ),
            )
            for k, g in itertools.groupby(
                self._session.scalars(stmt), lambda obj: obj.attribute_id
            )
        )

    def get_grouped_field_mapping_by_member_id(
        self,
        member_id: MemberID,
    ) -> frozendict[TaskID, FrozenFieldMappingIDToStringsT]:
        stmt = (
            select(MemberTaskModel.task_id, MemberFieldSlotModel)
            .join(
                MemberTaskModel,
                MemberTaskModel.member_task_id == MemberFieldSlotModel.member_task_id,
            )
            .where(
                MemberTaskModel.member_id == member_id,
            )
            .order_by(
                MemberTaskModel.task_id.asc(),
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
                            FieldSlotStr._create_from_real_and_hash(
                                obj.slot,
                                obj.slot_hash,
                            )
                            for _, obj in attr_group
                        ),
                    )
                    for attr_id, attr_group in itertools.groupby(
                        task_group,
                        lambda row: row[1].attribute_id,
                    )
                ),
            )
            for task_id, task_group in itertools.groupby(
                self._session.execute(stmt).tuples(),
                lambda row: row[0],
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
