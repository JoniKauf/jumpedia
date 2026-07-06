import types as ts
import typing as t

from sqlalchemy import select

from db.models import AttributeModel, MemberFieldSlotModel
from domain.entities.member_field_slot import MemberFieldSlotEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.types.member_task import MemberTaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index
from repositories.base import BaseRepository
from repositories.dtos.member_field_slot import MemberFieldSlotInsert


def member_field_slot_model_to_entity(
    model: MemberFieldSlotModel,
) -> MemberFieldSlotEntity:
    return MemberFieldSlotEntity(
        member_task_id=model.member_task_id,
        attribute_id=model.attribute_id,
        index=Index(model.index),
        slot=FieldSlotStr(_real=model.real_slot, _norm=model.norm_slot),
    )


class MemberFieldSlotRepository(BaseRepository):
    def create_many(
        self, member_field_slots: t.Iterable[MemberFieldSlotInsert]
    ) -> tuple[MemberFieldSlotEntity, ...]:
        """Preserves order."""
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

        return tuple(member_field_slot_model_to_entity(obj) for obj in objs)

    def get_field_mapping_by_member_task_id(
        self, member_task_id: MemberTaskID, types: t.AbstractSet[AttributeType]
    ) -> frozendict[AttributeID, tuple[MemberFieldSlotEntity, ...]]:
        stmt = (
            select(MemberFieldSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == MemberFieldSlotModel.attribute_id,
            )
            .where(
                MemberFieldSlotModel.member_task_id == member_task_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                MemberFieldSlotModel.attribute_id.asc(),
                MemberFieldSlotModel.index.asc(),
            )
        )

        res: dict[AttributeID, list[MemberFieldSlotEntity]] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.attribute_id, []).append(
                member_field_slot_model_to_entity(obj)
            )

        return frozendict({k: tuple(v) for k, v in res.items()})

    def get_field_mapping_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
    ) -> frozendict[
        MemberTaskID,
        frozendict[AttributeID, tuple[MemberFieldSlotEntity, ...]],
    ]:
        stmt = (
            select(MemberFieldSlotModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == MemberFieldSlotModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                MemberFieldSlotModel.member_task_id.asc(),
                MemberFieldSlotModel.attribute_id.asc(),
                MemberFieldSlotModel.index.asc(),
            )
        )

        res: dict[
            MemberTaskID,
            dict[AttributeID, list[MemberFieldSlotEntity]],
        ] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.member_task_id, {}).setdefault(
                obj.attribute_id, []
            ).append(member_field_slot_model_to_entity(obj))

        return frozendict(
            {
                task_id: frozendict(
                    {attr_id: tuple(slots) for attr_id, slots in attr_map.items()}
                )
                for task_id, attr_map in res.items()
            }
        )
