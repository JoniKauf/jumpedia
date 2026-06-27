import typing as t

from sqlalchemy import func, or_, select, text, update

from db.models import AttributeModel, AttributeAliasModel, ListModel
from domain import errors
from domain.entities.attribute import AttributeEntity, AttributeSlot
from domain.entities.community import CommunityEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.types.attribute import AttributeID
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSyn
from domain.value_objects.community import CommunityLimits
from domain.value_objects.position import Position
from domain.value_objects.string import Str
from repositories.base import BaseRepository
from repositories.dtos.attribute import AttributeAliasInsert, AttributeInsert


def attribute_model_to_entity(model: AttributeModel) -> AttributeEntity:
    return AttributeEntity(
        attribute_id=model.attribute_id,
        list_id=model.list_id,
        name=AttributeSyn(_real=model.real_name, _norm=model.norm_name),
        type=AttributeType(model.type),
        kind=AttributeKind(model.kind),
        slot=AttributeSlot(
            AttributeSlotType(model.slot_type),
            model.min_slot_count,
            model.max_slot_count,
        ),
        position=Position(model.position),
    )


class AttributeRepository(BaseRepository):
    def create(self, attribute: AttributeInsert) -> AttributeEntity:
        obj = AttributeModel(
            list_id=attribute.list_id,
            norm_name=attribute.name.norm,
            real_name=attribute.name.real,
            type=attribute.type,
            kind=attribute.kind.value,
            slot_type=attribute.slot.type,
            min_slot_count=attribute.slot.min_count,
            max_slot_count=attribute.slot.max_count,
            position=attribute.position.value,
        )

        self.session.add(obj)
        self.session.flush()

        return attribute_model_to_entity(obj)

    def create_many_aliases(
        self, attribute_aliases: t.Iterable[AttributeAliasInsert]
    ) -> None:
        objs = tuple(
            AttributeAliasModel(
                attribute_id=attr_alias.attribute_id,
                list_id=attr_alias.list_id,
                norm_alias=attr_alias.alias.norm,
                real_alias=attr_alias.alias.real,
            )
            for attr_alias in attribute_aliases
        )

        self.session.add_all(objs)
        self.session.flush()

    def delete(self, attribute_id: AttributeID) -> None:
        obj = self.session.get(AttributeModel, attribute_id)

        if obj is None:
            raise errors.NotFoundById(AttributeEntity)

        self.session.delete(obj)
        self.session.flush()

    def get_by_id(self, attribute_id: int) -> AttributeEntity | None:
        obj = self.session.get(AttributeModel, attribute_id)
        return None if obj is None else attribute_model_to_entity(obj)

    def get_all_by_list_id(self, list_id: int) -> list[AttributeEntity]:
        stmt = select(AttributeModel).where(AttributeModel.list_id == list_id)
        objs = self.session.scalars(stmt).all()
        return [attribute_model_to_entity(o) for o in objs]

    def get_by_list_id_and_name(
        self,
        list_id: ListID,
        name: AttributeSyn,
    ) -> AttributeEntity | None:
        stmt = select(AttributeModel).where(
            AttributeModel.list_id == list_id,
            AttributeModel.norm_name == name.norm,
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else attribute_model_to_entity(obj)

    def get_by_list_id_and_any_syn(
        self,
        list_id: ListID,
        syns: t.Iterable[AttributeSyn],
    ) -> tuple[AttributeEntity, AttributeSyn] | None:
        syns = tuple(syns)
        norms = {syn.norm for syn in syns}

        if not norms:
            return None

        stmt = (
            select(AttributeModel, AttributeAliasModel)
            .outerjoin(
                AttributeAliasModel,
                AttributeAliasModel.attribute_id == AttributeModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                or_(
                    AttributeModel.norm_name.in_(norms),
                    AttributeAliasModel.norm_alias.in_(norms),
                ),
            )
            .limit(1)
        )

        row = self.session.execute(stmt).first()

        if row is None:
            return None

        attr_obj, alias_obj = row
        attr_obj: AttributeModel
        alias_obj: AttributeAliasModel | None

        entity = attribute_model_to_entity(attr_obj)

        if attr_obj.norm_name in norms:
            syn = AttributeSyn(
                _real=attr_obj.real_name,
                _norm=attr_obj.norm_name,
            )
        else:
            assert alias_obj is not None
            syn = AttributeSyn(
                _real=alias_obj.real_alias,
                _norm=alias_obj.norm_alias,
            )

        return entity, syn

    def get_by_list_id_and_alias(
        self,
        list_id: ListID,
        alias: Str,
    ) -> AttributeEntity | None:
        stmt = (
            select(AttributeModel)
            .join(AttributeAliasModel, AttributeAliasModel.attribute_id == AttributeModel.attribute_id)
            .where(
                AttributeModel.list_id == list_id,
                AttributeAliasModel.norm_alias == alias.norm,
            )
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else attribute_model_to_entity(obj)

    def get_grouped_by_list_id(
        self,
        community_id: CommunityID,
    ) -> dict[ListID, list[AttributeEntity]]:
        stmt = (
            select(AttributeModel)
            .join(ListModel, ListModel.list_id == AttributeModel.list_id)
            .where(ListModel.community_id == community_id)
        )

        res: dict[ListID, list[AttributeEntity]] = {}

        for obj in self.session.scalars(stmt):
            res.setdefault(obj.list_id, []).append(attribute_model_to_entity(obj))

        return res

    def count_by_list(self, list_id: ListID) -> int:
        stmt = (
            select(func.count())
            .select_from(AttributeModel)
            .where(AttributeModel.list_id == list_id)
        )
        return self.session.scalar(stmt) or 0

    def decrement_positions_after(self, list_id: ListID, position: Position) -> None:
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
                "position": position.value,
            },
        )

        self.session.flush()

    def get_syn_to_attribute_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType]
    ) -> dict[AttributeSyn, AttributeEntity]:
        stmt = (
            select(AttributeModel, AttributeAliasModel)
            .outerjoin(
                AttributeAliasModel,
                AttributeAliasModel.attribute_id == AttributeModel.attribute_id,
            )
            .where(AttributeModel.list_id == list_id)
            .where(AttributeModel.type.in_(types))
        )

        res: dict[AttributeSyn, AttributeEntity] = {}
        id_to_entity: dict[AttributeID, AttributeEntity] = {}

        for attr_obj, alias_obj in self.session.execute(stmt):
            attr_obj: AttributeModel
            alias_obj: AttributeAliasModel | None

            entity = id_to_entity.get(attr_obj.attribute_id)

            if entity is None:
                entity = attribute_model_to_entity(attr_obj)
                id_to_entity[attr_obj.attribute_id] = entity 
                res[entity.name] = entity

            if alias_obj is not None:
                res[AttributeSyn(
                    _real=alias_obj.real_alias,
                    _norm=alias_obj.norm_alias)
                ] = entity

        return res