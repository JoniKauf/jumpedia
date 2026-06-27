import typing as t

from sqlalchemy import func, or_, select

from db.models import AttributeModel, AttributeCollectionEntryModel, AttributeCollectionEntryAliasModel
from domain import errors
from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.types.list import ListID
from domain.value_objects.task_attribute_slot import TaskAttributeSlot
from repositories.base import BaseRepository
from repositories.dtos.attribute_collection_entry import (
    AttributeCollectionEntryAliasInsert,
    AttributeCollectionEntryInsert,
    AttributeCollectionEntryWithAliases,
)


def attribute_collection_entry_model_to_entity(
    model: AttributeCollectionEntryModel,
) -> AttributeCollectionEntryEntity:
    return AttributeCollectionEntryEntity(
        model.attribute_collection_entry_id,
        model.attribute_id,
        TaskAttributeSlot(_real=model.real_value, _norm=model.norm_value),
    )


class AttributeCollectionEntryRepository(BaseRepository):
    def create_many(
        self, entries: t.Iterable[AttributeCollectionEntryInsert]
    ) -> list[AttributeCollectionEntryEntity]:
        """Preserves order."""
        objs = tuple(
            AttributeCollectionEntryModel(
                attribute_id=entry.attribute_id,
                index=entry.index.value,
                norm_value=entry.value.norm,
                real_value=entry.value.real,
            )
            for entry in entries
        )

        self.session.add_all(objs)
        self.session.flush()

        return [attribute_collection_entry_model_to_entity(obj) for obj in objs]

    def create_many_aliases(
        self, entry_aliases: t.Iterable[AttributeCollectionEntryAliasInsert]
    ) -> None:
        objs = tuple(
            AttributeCollectionEntryAliasModel(
                attribute_collection_entry_id=entry_alias.attribute_collection_entry_id,
                attribute_id=entry_alias.attribute_id,
                norm_alias=entry_alias.alias.norm,
                real_alias=entry_alias.alias.real,
            )
            for entry_alias in entry_aliases
        )

        self.session.add_all(objs)
        self.session.flush()

    def get_by_id(
        self,
        entry_id: AttributeCollectionEntryID,
    ) -> AttributeCollectionEntryEntity | None:
        obj = self.session.get(AttributeCollectionEntryModel, entry_id)

        return None if obj is None else attribute_collection_entry_model_to_entity(obj)

    def get_all_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> list[AttributeCollectionEntryEntity]:
        stmt = (
            select(AttributeCollectionEntryModel)
            .where(AttributeCollectionEntryModel.attribute_id == attribute_id)
            .order_by(AttributeCollectionEntryModel.index.asc())
        )

        return [
            attribute_collection_entry_model_to_entity(obj)
            for obj in self.session.scalars(stmt)
        ]

    def get_by_attribute_id_and_name(
        self,
        attribute_id: AttributeID,
        name: TaskAttributeSlot,
    ) -> AttributeCollectionEntryEntity | None:
        stmt = select(AttributeCollectionEntryModel).where(
            AttributeCollectionEntryModel.attribute_id == attribute_id,
            AttributeCollectionEntryModel.norm_value == name.norm,
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else attribute_collection_entry_model_to_entity(obj)

    def get_by_attribute_id_and_alias(
        self,
        attribute_id: AttributeID,
        alias: TaskAttributeSlot,
    ) -> AttributeCollectionEntryEntity | None:
        stmt = (
            select(AttributeCollectionEntryModel)
            .join(
                AttributeCollectionEntryAliasModel,
                AttributeCollectionEntryAliasModel.attribute_collection_entry_id
                == AttributeCollectionEntryModel.attribute_collection_entry_id,
            )
            .where(
                AttributeCollectionEntryModel.attribute_id == attribute_id,
                AttributeCollectionEntryAliasModel.norm_alias == alias.norm,
            )
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else attribute_collection_entry_model_to_entity(obj)

    def get_by_attribute_id_and_any_syn(
        self,
        attribute_id: AttributeID,
        syns: t.Iterable[TaskAttributeSlot],
    ) -> (
        tuple[
            AttributeCollectionEntryEntity,
            TaskAttributeSlot,
        ]
        | None
    ):
        norm_to_store = {syn.norm: syn for syn in syns}

        if not norm_to_store:
            return None

        stmt = (
            select(
                AttributeCollectionEntryModel,
                AttributeCollectionEntryModel.norm_value,
                AttributeCollectionEntryAliasModel.norm_alias,
            )
            .outerjoin(
                AttributeCollectionEntryAliasModel,
                AttributeCollectionEntryAliasModel.attribute_collection_entry_id
                == AttributeCollectionEntryModel.attribute_collection_entry_id,
            )
            .where(
                AttributeCollectionEntryModel.attribute_id == attribute_id,
                or_(
                    AttributeCollectionEntryModel.norm_value.in_(tuple(norm_to_store)),
                    AttributeCollectionEntryAliasModel.norm_alias.in_(tuple(norm_to_store)),
                ),
            )
            .limit(1)
        )

        row = self.session.execute(stmt).first()

        if row is None:
            return None

        obj, entry_norm, alias_norm = row

        matched_norm = entry_norm if entry_norm in norm_to_store else alias_norm

        return (
            attribute_collection_entry_model_to_entity(obj),
            norm_to_store[matched_norm],
        )

    def count_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AttributeCollectionEntryModel)
            .where(AttributeCollectionEntryModel.attribute_id == attribute_id)
        )

        return self.session.scalar(stmt) or 0

    def delete(
        self,
        entry_id: AttributeCollectionEntryID,
    ) -> None:
        obj = self.session.get(
            AttributeCollectionEntryModel,
            entry_id,
        )

        if obj is None:
            raise errors.NotFoundById(AttributeCollectionEntryEntity)

        self.session.delete(obj)
        self.session.flush()


    def get_grouped_collections_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
    ) -> dict[AttributeID, list[AttributeCollectionEntryWithAliases]]:
        stmt = (
            select(AttributeCollectionEntryModel, AttributeCollectionEntryAliasModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == AttributeCollectionEntryModel.attribute_id,
            )
            .outerjoin(
                AttributeCollectionEntryAliasModel,
                AttributeCollectionEntryAliasModel.attribute_collection_entry_id
                == AttributeCollectionEntryModel.attribute_collection_entry_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                AttributeCollectionEntryModel.attribute_id.asc(),
                AttributeCollectionEntryModel.index.asc(),
                AttributeCollectionEntryAliasModel.attribute_collection_entry_alias_id.asc(),
            )
        )

        entries: dict[AttributeCollectionEntryID, AttributeCollectionEntryEntity] = {}
        entry_aliases: dict[
            AttributeCollectionEntryID,
            list[TaskAttributeSlot],
        ] = {}
        grouped_entries: dict[
            AttributeID,
            list[AttributeCollectionEntryEntity],
        ] = {}

        for entry_obj, alias_obj in self.session.execute(stmt):
            entry_obj: AttributeCollectionEntryModel
            alias_obj: AttributeCollectionEntryAliasModel | None
            
            entry = entries.get(entry_obj.attribute_collection_entry_id)

            if entry is None:
                entry = attribute_collection_entry_model_to_entity(entry_obj)
                entries[entry.attribute_collection_entry_id] = entry
                grouped_entries.setdefault(entry.attribute_id, []).append(entry)

            if alias_obj is not None:
                entry_aliases.setdefault(entry.attribute_collection_entry_id, []).append(
                    TaskAttributeSlot(
                        _real=alias_obj.real_alias,
                        _norm=alias_obj.norm_alias,
                    )
                )

        return {
            attribute_id: [
                AttributeCollectionEntryWithAliases(
                    entry=entry,
                    aliases=tuple(entry_aliases.get(entry.attribute_collection_entry_id, ())),
                )
                for entry in collection
            ]
            for attribute_id, collection in grouped_entries.items()
        }