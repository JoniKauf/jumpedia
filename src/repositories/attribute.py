from sqlalchemy import select

from db.models import Attribute, List
from domain.entities.attribute import AttributeEntity, AttributeSlot
from domain.entities.community import CommunityEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.types.id import ID
from domain.value_objects.attribute import AttributeName
from domain.value_objects.community import CommunityLimits
from repositories.base import BaseRepository
import typing as t
from sqlalchemy import func

from repositories.dtos.attribute import CreateAttributeDTO

def _attribute_model_to_entity(model: Attribute) -> AttributeEntity:
    return AttributeEntity(
        id=model.attribute_id,
        list_id=model.list_id,
        name=AttributeName(_real=model.real_name, _norm=model.norm_name),
        type=AttributeType(model.type),
        kind=AttributeKind(model.kind),
        slot=AttributeSlot(
            AttributeSlotType(model.slot_type),
            model.min_slot_count,
            model.max_slot_count,
        ),
        position=model.position,
    )


class AttributeRepository(BaseRepository):
    def create(self, attribute: CreateAttributeDTO) -> AttributeEntity:
        obj = Attribute(
            list_id=attribute.list_id,
            norm_name=attribute.name.norm,
            real_name=attribute.name.real,
            type=attribute.type,
            kind=attribute.kind.value,
            slot_type=attribute.slot.type,
            min_slot_count=attribute.slot.min_count,
            max_slot_count=attribute.slot.max_count,
            position=attribute.position,
        )

        self.session.add(obj)
        self.session.flush()

        return _attribute_model_to_entity(obj)

    def get_by_id(self, attribute_id: int) -> AttributeEntity | None:
        obj = self.session.get(Attribute, attribute_id)
        return None if obj is None else _attribute_model_to_entity(obj)

    def get_all_by_list_id(self, list_id: int) -> list[AttributeEntity]:
        stmt = select(Attribute).where(Attribute.list_id == list_id)
        objs = self.session.scalars(stmt).all()
        return [_attribute_model_to_entity(o) for o in objs]

    def get_by_list_id_and_name(
        self,
        list_id: ID,
        name: AttributeName,
    ) -> AttributeEntity | None:
        stmt = select(Attribute).where(
            Attribute.list_id == list_id,
            Attribute.norm_name == name.norm,
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else _attribute_model_to_entity(obj)

    def get_grouped_by_list_id(
        self,
        community_id: ID,
    ) -> dict[ID, list[AttributeEntity]]:
        stmt = (
            select(Attribute)
            .join(List, List.list_id == Attribute.list_id)
            .where(List.community_id == community_id)
        )

        res: dict[ID, list[AttributeEntity]] = {}

        for obj in self.session.scalars(stmt):
            res.setdefault(ID(obj.list_id), []).append(
                _attribute_model_to_entity(obj)
            )

        return res
    
    def count_by_list(self, list_id: ID) -> int:
        stmt = (
            select(func.count())
            .select_from(Attribute)
            .where(Attribute.list_id == list_id)
        )
        return self.session.scalar(stmt) or 0