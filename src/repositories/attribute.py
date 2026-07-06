import types as ts
import typing as t

from sqlalchemy import case, delete, func, or_, select, text, update

from db.models import AttributeAliasModel, AttributeModel, ListModel
from domain import errors
from domain.entities.attribute import AttributeEntity, AttributeSlot
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.types.attribute import AttributeID
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.index import Index
from domain.value_objects.position import Position
from domain.value_objects.string import Str
from repositories.base import BaseRepository
from repositories.dtos.attribute import AttributeAliasInsert, AttributeInsert


def attribute_model_to_entity(model: AttributeModel) -> AttributeEntity[t.Any]:
    return AttributeEntity(
        attribute_id=model.attribute_id,
        list_id=model.list_id,
        name=AttributeSynStr(_real=model.real_name, _norm=model.norm_name),
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
    def create[T: AttributeType](
        self, attribute: AttributeInsert[T]
    ) -> AttributeEntity[T]:
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

        self._session.add(obj)
        self._session.flush()

        return attribute_model_to_entity(obj)

    def create_many_aliases(
        self, attribute_aliases: t.Iterable[AttributeAliasInsert]
    ) -> None:
        objs = tuple(
            AttributeAliasModel(
                attribute_id=attr_alias.attribute_id,
                index=attr_alias.index.value,
                list_id=attr_alias.list_id,
                norm_alias=attr_alias.alias.norm,
                real_alias=attr_alias.alias.real,
            )
            for attr_alias in attribute_aliases
        )

        self._session.add_all(objs)
        self._session.flush()

    def delete(self, attribute_id: AttributeID) -> None:
        obj = self._session.get(AttributeModel, attribute_id)

        if obj is None:
            raise errors.NotFoundById(AttributeEntity)

        self._session.delete(obj)
        self._session.flush()

    def get_by_id(self, attribute_id: AttributeID) -> AttributeEntity | None:
        obj = self._session.get(AttributeModel, attribute_id)
        return None if obj is None else attribute_model_to_entity(obj)

    def get_all_by_list_id[T: AttributeType](
        self, list_id: ListID, types: t.AbstractSet[T]
    ) -> tuple[AttributeEntity[T], ...]:
        stmt = (
            select(AttributeModel)
            .where(AttributeModel.list_id == list_id)
            .where(AttributeModel.type.in_(types))
            .order_by(AttributeModel.position.asc())
        )
        objs = self._session.scalars(stmt).all()
        entities: tuple[AttributeEntity[T], ...] = tuple(
            attribute_model_to_entity(o) for o in objs
        )

        return entities

    def get_by_list_id_and_name(
        self,
        list_id: ListID,
        name: AttributeSynStr,
    ) -> AttributeEntity | None:
        stmt = select(AttributeModel).where(
            AttributeModel.list_id == list_id,
            AttributeModel.norm_name == name.norm,
        )

        obj = self._session.scalar(stmt)

        return None if obj is None else attribute_model_to_entity(obj)

    def get_first_by_list_id_and_any_syn(
        self,
        list_id: ListID,
        syns: t.Iterable[AttributeSynStr],
        exclude: AttributeID | None,
    ) -> tuple[AttributeEntity, AttributeSynStr] | None:
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

        if exclude is not None:
            stmt = stmt.where(AttributeModel.attribute_id != exclude)

        row = self._session.execute(stmt).first()

        if row is None:
            return None

        attr_obj, alias_obj = row
        attr_obj: AttributeModel
        alias_obj: AttributeAliasModel | None

        entity = attribute_model_to_entity(attr_obj)

        if attr_obj.norm_name in norms:
            syn = AttributeSynStr(
                _real=attr_obj.real_name,
                _norm=attr_obj.norm_name,
            )
        else:
            assert alias_obj is not None
            syn = AttributeSynStr(
                _real=alias_obj.real_alias,
                _norm=alias_obj.norm_alias,
            )

        return entity, syn

    def get_by_list_id_and_syn(
        self,
        list_id: ListID,
        syn: AttributeSynStr,
    ) -> tuple[AttributeEntity, AttributeSynStr] | None:
        stmt = (
            select(AttributeModel, AttributeAliasModel)
            .outerjoin(
                AttributeAliasModel,
                AttributeAliasModel.attribute_id == AttributeModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                or_(
                    AttributeModel.norm_name == syn.norm,
                    AttributeAliasModel.norm_alias == syn.norm,
                ),
            )
            .limit(1)
        )

        row = self._session.execute(stmt).first()

        if row is None:
            return None

        attr_obj, alias_obj = row
        attr_obj: AttributeModel
        alias_obj: AttributeAliasModel | None

        entity = attribute_model_to_entity(attr_obj)

        if attr_obj.norm_name == syn.norm:
            colliding_syn = AttributeSynStr(
                _real=attr_obj.real_name,
                _norm=attr_obj.norm_name,
            )
        else:
            assert alias_obj is not None
            colliding_syn = AttributeSynStr(
                _real=alias_obj.real_alias,
                _norm=alias_obj.norm_alias,
            )

        return entity, colliding_syn

    def get_by_list_id_and_alias(
        self,
        list_id: ListID,
        alias: Str,
    ) -> AttributeEntity | None:
        stmt = (
            select(AttributeModel)
            .join(
                AttributeAliasModel,
                AttributeAliasModel.attribute_id == AttributeModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeAliasModel.norm_alias == alias.norm,
            )
        )

        obj = self._session.scalar(stmt)

        return None if obj is None else attribute_model_to_entity(obj)

    def get_grouped_by_list_id(
        self,
        community_id: CommunityID,
    ) -> frozendict[ListID, list[AttributeEntity]]:
        stmt = (
            select(AttributeModel)
            .join(ListModel, ListModel.list_id == AttributeModel.list_id)
            .where(ListModel.community_id == community_id)
            .order_by(ListModel.list_id.asc(), AttributeModel.position.asc())
        )

        res: dict[ListID, list[AttributeEntity]] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.list_id, []).append(attribute_model_to_entity(obj))

        return frozendict(
            res
        )  # pyright: ignore[reportCallIssue]  Pyright bug for beta 3.15

    def count_by_list(self, list_id: ListID) -> int:
        stmt = (
            select(func.count())
            .select_from(AttributeModel)
            .where(AttributeModel.list_id == list_id)
        )
        return self._session.scalar(stmt) or 0

    def decrement_positions_after(self, list_id: ListID, position: Position) -> None:
        # Unique situation where we have need to decrement n positions, but all are unique
        # We use mariadbs order by which is made for this reason. Though not directly supported
        # by sqlalchemy, so we use raw sql

        self._session.execute(
            text("""
                UPDATE attribute
                SET position = position - 1
                WHERE list_id = :list_id
                AND position > :position
                ORDER BY position ASC
                """),
            {
                "list_id": list_id,
                "position": position.value,
            },
        )

        self._session.flush()

    def get_syn_to_attribute_by_list_id[T: AttributeType](
        self, list_id: ListID, types: t.AbstractSet[T]
    ) -> frozendict[AttributeSynStr, AttributeEntity[T]]:
        stmt = (
            select(AttributeModel, AttributeAliasModel)
            .outerjoin(
                AttributeAliasModel,
                AttributeAliasModel.attribute_id == AttributeModel.attribute_id,
            )
            .where(AttributeModel.list_id == list_id)
            .where(AttributeModel.type.in_(types))
        )

        res: dict[AttributeSynStr, AttributeEntity[T]] = {}
        id_to_entity: dict[AttributeID, AttributeEntity[T]] = {}

        for attr_obj, alias_obj in self._session.execute(stmt):
            attr_obj: AttributeModel
            alias_obj: AttributeAliasModel | None

            entity: AttributeEntity[T] | None = id_to_entity.get(attr_obj.attribute_id)

            if entity is None:
                entity = attribute_model_to_entity(attr_obj)
                id_to_entity[attr_obj.attribute_id] = entity
                res[entity.name] = entity

            if alias_obj is not None:
                res[
                    AttributeSynStr(
                        _real=alias_obj.real_alias, _norm=alias_obj.norm_alias
                    )
                ] = entity

        return frozendict(
            res
        )  # pyright: ignore[reportCallIssue]  Pyright bug for beta 3.15

    def get_aliases_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> tuple[AttributeSynStr, ...]:
        stmt = (
            select(AttributeAliasModel)
            .where(AttributeAliasModel.attribute_id == attribute_id)
            .order_by(AttributeAliasModel.index.asc())
        )

        return tuple(
            AttributeSynStr(
                _real=obj.real_alias,
                _norm=obj.norm_alias,
            )
            for obj in self._session.scalars(stmt)
        )

    def get_grouped_aliases_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
    ) -> frozendict[AttributeID, tuple[AttributeSynStr, ...]]:
        stmt = (
            select(AttributeAliasModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == AttributeAliasModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.type.in_(types),
            )
            .order_by(AttributeModel.position.asc(), AttributeAliasModel.index.asc())
        )

        res: dict[AttributeID, list[AttributeSynStr]] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.attribute_id, []).append(
                AttributeSynStr(
                    _real=obj.real_alias,
                    _norm=obj.norm_alias,
                )
            )

        return frozendict(
            {
                attribute_id: tuple(aliases) for attribute_id, aliases in res.items()
            }  # pyright: ignore[reportCallIssue]  Pyright bug for beta 3.15
        )

    def update_name(
        self,
        attribute_id: AttributeID,
        name: AttributeSynStr,
    ) -> None:
        obj = self._session.get(AttributeModel, attribute_id)

        if obj is None:
            raise errors.NotFoundById(AttributeEntity)

        obj.real_name = name.real
        obj.norm_name = name.norm

        self._session.flush()

    def update_aliases(
        self,
        attribute_id: AttributeID,
        aliases: t.Iterable[AttributeAliasInsert],
    ) -> None:
        self._session.execute(
            delete(AttributeAliasModel).where(
                AttributeAliasModel.attribute_id == attribute_id,
            )
        )

        objs = tuple(
            AttributeAliasModel(
                attribute_id=attribute_id,
                index=alias.index.value,
                list_id=alias.list_id,
                real_alias=alias.alias.real,
                norm_alias=alias.alias.norm,
            )
            for alias in aliases
        )

        if objs:
            self._session.add_all(objs)

        self._session.flush()

    def update_min_and_max_slot_count(
        self, attribute_id: AttributeID, min_slot_count: int, max_slot_count: int
    ) -> None:
        obj = self._session.get(AttributeModel, attribute_id)

        if obj is None:
            raise errors.NotFoundById(AttributeEntity)

        obj.min_slot_count = min_slot_count
        obj.max_slot_count = max_slot_count

        self._session.flush()

    def update_positions(
        self,
        list_id: ListID,
        all_ordered_attribute_ids: tuple[AttributeID, ...],
    ) -> None:
        offset = len(all_ordered_attribute_ids)

        # 1) move everything out of UNIQUE range
        self._session.execute(
            update(AttributeModel)
            .where(AttributeModel.list_id == list_id)
            .values(position=AttributeModel.position + offset)
        )

        # 2) assign final positions in one batch (CASE update)
        position_case = case(
            {
                attr_id: pos
                for pos, attr_id in enumerate(all_ordered_attribute_ids, start=1)
            },
            value=AttributeModel.attribute_id,
        )

        self._session.execute(
            update(AttributeModel)
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.attribute_id.in_(all_ordered_attribute_ids),
            )
            .values(position=position_case)
        )

        self._session.flush()
