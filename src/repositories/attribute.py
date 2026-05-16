from sqlalchemy import select

from db.models import Attribute
from domain.entities.attribute import AttributeEntity, Slot
from domain.enums.attribute import Kind, SlotType, Type
from domain.value_objects.limits import Limits
from interfaces.list import StrStore
from repositories.base import BaseRepository


def _model_to_entity(model: Attribute, limits: Limits) -> AttributeEntity:
    return AttributeEntity(
        _id=model.attribute_id,
        _list_id=model.list_id,
        _type=Type(model.type),
        _kind=Kind(model.kind),
        _name=StrStore(_real=model.real_name, _norm=model.norm_name),
        _slot=Slot(SlotType(model.slot_type), model.min_slot_count, model.max_slot_count, limits),
        _position=model.position,
    )


class AttributeRepository(BaseRepository):
    def get_by_id(self, attribute_id: int, limits: Limits) -> AttributeEntity | None:
        obj = self.session.get(Attribute, attribute_id)
        return None if obj is None else _model_to_entity(obj, limits)

    def get_by_list_id(self, list_id: int, limits: Limits) -> list[AttributeEntity]:
        stmt = select(Attribute).where(Attribute.list_id == list_id)
        objs = self.session.scalars(stmt).all()
        return [_model_to_entity(o, limits) for o in objs]