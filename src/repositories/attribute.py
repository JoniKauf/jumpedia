from sqlalchemy import select

from db.models import Attribute
from domain.entities.attribute import AttributeEntity, AttributeSlot
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.value_objects.limits import Limits
from interfaces.list import StrStore
from repositories.base import BaseRepository


def _attribute_model_to_entity(model: Attribute, limits: Limits) -> AttributeEntity:
    return AttributeEntity(
        id=model.attribute_id,
        list_id=model.list_id,
        type=AttributeType(model.type),
        kind=AttributeKind(model.kind),
        name=StrStore(_real=model.real_name, _norm=model.norm_name),
        slot=AttributeSlot(
            AttributeSlotType(model.slot_type),
            model.min_slot_count,
            model.max_slot_count,
            limits,
        ),
        position=model.position,
    )


class AttributeRepository(BaseRepository):
    def get_by_id(self, attribute_id: int, limits: Limits) -> AttributeEntity | None:
        obj = self.session.get(Attribute, attribute_id)
        return None if obj is None else _attribute_model_to_entity(obj, limits)

    def get_by_list_id(self, list_id: int, limits: Limits) -> list[AttributeEntity]:
        stmt = select(Attribute).where(Attribute.list_id == list_id)
        objs = self.session.scalars(stmt).all()
        return [_attribute_model_to_entity(o, limits) for o in objs]
