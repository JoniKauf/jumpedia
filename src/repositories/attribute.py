from sqlalchemy import select, text, update

from db.models import Attribute, AttributeAlias, List
from domain import errors
from domain.entities.attribute import AttributeEntity, AttributeSlot
from domain.entities.community import CommunityEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.types.attribute import AttributeID
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeName
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore
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

    def delete(self, attribute_id: AttributeID) -> None:
        obj = self.session.get(Attribute, attribute_id)

        if obj is None:
            raise errors.NotFoundById(AttributeEntity)

        self.session.delete(obj)
        self.session.flush()

    def get_by_id(self, attribute_id: int) -> AttributeEntity | None:
        obj = self.session.get(Attribute, attribute_id)
        return None if obj is None else _attribute_model_to_entity(obj)

    def get_all_by_list_id(self, list_id: int) -> list[AttributeEntity]:
        stmt = select(Attribute).where(Attribute.list_id == list_id)
        objs = self.session.scalars(stmt).all()
        return [_attribute_model_to_entity(o) for o in objs]

    def get_by_list_id_and_name(
        self,
        list_id: ListID,
        name: AttributeName,
    ) -> AttributeEntity | None:
        stmt = select(Attribute).where(
            Attribute.list_id == list_id,
            Attribute.norm_name == name.norm,
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else _attribute_model_to_entity(obj)

    def get_by_list_id_and_alias(
        self,
        list_id: ListID,
        alias: StrStore,
    ) -> AttributeEntity | None:
        stmt = (
            select(Attribute)
            .join(AttributeAlias, AttributeAlias.attribute_id == Attribute.attribute_id)
            .where(
                Attribute.list_id == list_id,
                AttributeAlias.norm_alias == alias.norm,
            )
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else _attribute_model_to_entity(obj)

    def get_grouped_by_list_id(
        self,
        community_id: CommunityID,
    ) -> dict[ListID, list[AttributeEntity]]:
        stmt = (
            select(Attribute)
            .join(List, List.list_id == Attribute.list_id)
            .where(List.community_id == community_id)
        )

        res: dict[ListID, list[AttributeEntity]] = {}

        for obj in self.session.scalars(stmt):
            res.setdefault(obj.list_id, []).append(_attribute_model_to_entity(obj))

        return res

    def count_by_list(self, list_id: ListID) -> int:
        stmt = (
            select(func.count())
            .select_from(Attribute)
            .where(Attribute.list_id == list_id)
        )
        return self.session.scalar(stmt) or 0

    def decrement_positions_after(self, list_id: ListID, position: int) -> None:
        # Unique situation where we have need to decrement n positions, but all are unique
        # We use mariadbs order by which is made for this reason. Though not directly supported
        # by sqlalchemy, so we use raw sql

        self.session.execute(
            text(
                """
                UPDATE attribute
                SET position = position - 1
                WHERE list_id = :list_id
                AND position > :position
                ORDER BY position ASC
                """
            ),
            {
                "list_id": list_id,
                "position": position,
            },
        )

        self.session.flush()