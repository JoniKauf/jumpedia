import typing as t

from sqlalchemy import func, or_, select

from db.models import Attribute, AttributeCollectionEntry, AttributeCollectionEntryAlias
from domain import errors
from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.types.list import ListID
from domain.value_objects.attribute_collection_entry import AttributeCollectionEntrySyn
from repositories.base import BaseRepository
from repositories.dtos.attribute_collection_entry import (
    AttributeCollectionEntryAliasInsert,
    AttributeCollectionEntryInsert,
    AttributeCollectionEntryWithAliases,
)


def attribute_collection_entry_model_to_entity(
    model: AttributeCollectionEntry,
) -> AttributeCollectionEntryEntity:
    return AttributeCollectionEntryEntity(
        model.attribute_collection_entry_id,
        model.attribute_id,
        AttributeCollectionEntrySyn(_real=model.real_value, _norm=model.norm_value),
    )


class AttributeCollectionEntryRepository(BaseRepository):
    def create_many(
        self, entries: t.Iterable[AttributeCollectionEntryInsert]
    ) -> list[AttributeCollectionEntryEntity]:
        """Preserves order."""
        objs = tuple(
            AttributeCollectionEntry(
                attribute_id=entry.attribute_id,
                index=entry.index,
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
            AttributeCollectionEntryAlias(
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
        obj = self.session.get(AttributeCollectionEntry, entry_id)

        return None if obj is None else attribute_collection_entry_model_to_entity(obj)

    def get_all_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> list[AttributeCollectionEntryEntity]:
        stmt = (
            select(AttributeCollectionEntry)
            .where(AttributeCollectionEntry.attribute_id == attribute_id)
            .order_by(AttributeCollectionEntry.index.asc())
        )

        return [
            attribute_collection_entry_model_to_entity(obj)
            for obj in self.session.scalars(stmt)
        ]

    def get_by_attribute_id_and_name(
        self,
        attribute_id: AttributeID,
        name: AttributeCollectionEntrySyn,
    ) -> AttributeCollectionEntryEntity | None:
        stmt = select(AttributeCollectionEntry).where(
            AttributeCollectionEntry.attribute_id == attribute_id,
            AttributeCollectionEntry.norm_value == name.norm,
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else attribute_collection_entry_model_to_entity(obj)

    def get_by_attribute_id_and_alias(
        self,
        attribute_id: AttributeID,
        alias: AttributeCollectionEntrySyn,
    ) -> AttributeCollectionEntryEntity | None:
        stmt = (
            select(AttributeCollectionEntry)
            .join(
                AttributeCollectionEntryAlias,
                AttributeCollectionEntryAlias.attribute_collection_entry_id
                == AttributeCollectionEntry.attribute_collection_entry_id,
            )
            .where(
                AttributeCollectionEntry.attribute_id == attribute_id,
                AttributeCollectionEntryAlias.norm_alias == alias.norm,
            )
        )

        obj = self.session.scalar(stmt)

        return None if obj is None else attribute_collection_entry_model_to_entity(obj)

    def get_by_attribute_id_and_any_syn(
        self,
        attribute_id: AttributeID,
        syns: t.Iterable[AttributeCollectionEntrySyn],
    ) -> (
        tuple[
            AttributeCollectionEntryEntity,
            AttributeCollectionEntrySyn,
        ]
        | None
    ):
        norm_to_store = {syn.norm: syn for syn in syns}

        if not norm_to_store:
            return None

        stmt = (
            select(
                AttributeCollectionEntry,
                AttributeCollectionEntry.norm_value,
                AttributeCollectionEntryAlias.norm_alias,
            )
            .outerjoin(
                AttributeCollectionEntryAlias,
                AttributeCollectionEntryAlias.attribute_collection_entry_id
                == AttributeCollectionEntry.attribute_collection_entry_id,
            )
            .where(
                AttributeCollectionEntry.attribute_id == attribute_id,
                or_(
                    AttributeCollectionEntry.norm_value.in_(tuple(norm_to_store)),
                    AttributeCollectionEntryAlias.norm_alias.in_(tuple(norm_to_store)),
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
            .select_from(AttributeCollectionEntry)
            .where(AttributeCollectionEntry.attribute_id == attribute_id)
        )

        return self.session.scalar(stmt) or 0

    def delete(
        self,
        entry_id: AttributeCollectionEntryID,
    ) -> None:
        obj = self.session.get(
            AttributeCollectionEntry,
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
            select(AttributeCollectionEntry, AttributeCollectionEntryAlias)
            .join(
                Attribute,
                Attribute.attribute_id == AttributeCollectionEntry.attribute_id,
            )
            .outerjoin(
                AttributeCollectionEntryAlias,
                AttributeCollectionEntryAlias.attribute_collection_entry_id
                == AttributeCollectionEntry.attribute_collection_entry_id,
            )
            .where(
                Attribute.list_id == list_id,
                Attribute.type.in_(types),
            )
            .order_by(
                AttributeCollectionEntry.attribute_id.asc(),
                AttributeCollectionEntry.index.asc(),
                AttributeCollectionEntryAlias.attribute_collection_entry_alias_id.asc(),
            )
        )

        entries: dict[AttributeCollectionEntryID, AttributeCollectionEntryEntity] = {}
        entry_aliases: dict[
            AttributeCollectionEntryID,
            list[AttributeCollectionEntrySyn],
        ] = {}
        grouped_entries: dict[
            AttributeID,
            list[AttributeCollectionEntryEntity],
        ] = {}

        for entry_obj, alias_obj in self.session.execute(stmt):
            entry_obj: AttributeCollectionEntry
            alias_obj: AttributeCollectionEntryAlias | None
            
            entry = entries.get(entry_obj.attribute_collection_entry_id)

            if entry is None:
                entry = attribute_collection_entry_model_to_entity(entry_obj)
                entries[entry.id] = entry
                grouped_entries.setdefault(entry.attribute_id, []).append(entry)

            if alias_obj is not None:
                entry_aliases.setdefault(entry.id, []).append(
                    AttributeCollectionEntrySyn(
                        _real=alias_obj.real_alias,
                        _norm=alias_obj.norm_alias,
                    )
                )

        return {
            attribute_id: [
                AttributeCollectionEntryWithAliases(
                    entry=entry,
                    aliases=tuple(entry_aliases.get(entry.id, ())),
                )
                for entry in collection
            ]
            for attribute_id, collection in grouped_entries.items()
        }