import itertools
import typing as t
from operator import itemgetter

from sqlalchemy import delete, select

from jumpedia.db.models import MemberFieldSlotModel, MemberTaskModel
from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.field_mapping import FrozenFieldMappingIDToStringsT
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.member import MemberID
from jumpedia.domain.typing.member_task import MemberTaskID
from jumpedia.domain.typing.task import TaskID
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.repositories.base import BaseRepository
from jumpedia.repositories.dtos.member_field_slot import MemberFieldSlotInsert


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

    from operator import itemgetter

    def get_grouped_field_mapping_by_member_id_and_list_id(
        self,
        member_id: MemberID,
        list_id: ListID,
    ) -> frozendict[TaskID, FrozenFieldMappingIDToStringsT]:
        stmt = (
            select(
                MemberTaskModel.task_id,
                MemberFieldSlotModel.attribute_id,
                MemberFieldSlotModel.slot,
                MemberFieldSlotModel.slot_hash,
            )
            .join(
                MemberTaskModel,
                MemberTaskModel.member_task_id == MemberFieldSlotModel.member_task_id,
            )
            .where(
                MemberTaskModel.member_id == member_id,
                MemberTaskModel.list_id == list_id,
            )
            .order_by(
                MemberTaskModel.task_id,
                MemberFieldSlotModel.attribute_id,
                MemberFieldSlotModel.index,
            )
        )

        create = FieldSlotStr._create_from_real_and_hash
        get_task_id = itemgetter(0)
        get_attr_id = itemgetter(1)

        res: dict[TaskID, FrozenFieldMappingIDToStringsT] = {}

        rows = self._session.execute(stmt).tuples()

        for task_id, task_group in itertools.groupby(
            rows,
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
