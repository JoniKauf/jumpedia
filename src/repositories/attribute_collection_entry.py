from sqlalchemy import func, or_, select

from db.models import AttributeCollectionEntry, AttributeCollectionEntryAlias
from domain import errors
from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.value_objects.attribute_collection_entry import AttributeCollectionEntrySyn
from repositories.base import BaseRepository
import typing as t

def _attribute_collection_entry_model_to_entity(model: AttributeCollectionEntry) -> AttributeCollectionEntryEntity:
    return AttributeCollectionEntryEntity(
        model.attribute_collection_entry_id,
        model.attribute_id,
        AttributeCollectionEntrySyn(
            _real=model.real_slot,
            _norm=model.norm_slot
        )
    )

class AttributeCollectionEntryRepository(BaseRepository):
    def get_by_id(
        self,
        entry_id: AttributeCollectionEntryID,
    ) -> AttributeCollectionEntryEntity | None:
        obj = self.session.get(AttributeCollectionEntry, entry_id)

        return (
            None
            if obj is None
            else _attribute_collection_entry_model_to_entity(obj)
        )

    def get_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> list[AttributeCollectionEntryEntity]:
        stmt = (
            select(AttributeCollectionEntry)
            .where(AttributeCollectionEntry.attribute_id == attribute_id)
            .order_by(AttributeCollectionEntry.index.asc())
        )

        return [
            _attribute_collection_entry_model_to_entity(obj)
            for obj in self.session.scalars(stmt)
        ]

    def get_by_attribute_id_and_name(
        self,
        attribute_id: AttributeID,
        name: AttributeCollectionEntrySyn,
    ) -> AttributeCollectionEntryEntity | None:
        stmt = select(AttributeCollectionEntry).where(
            AttributeCollectionEntry.attribute_id == attribute_id,
            AttributeCollectionEntry.norm_slot == name.norm,
        )

        obj = self.session.scalar(stmt)

        return (
            None
            if obj is None
            else _attribute_collection_entry_model_to_entity(obj)
        )

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

        return (
            None
            if obj is None
            else _attribute_collection_entry_model_to_entity(obj)
        )

    def get_by_attribute_id_and_any_identifier(
        self,
        attribute_id: AttributeID,
        syns: t.Iterable[AttributeCollectionEntrySyn],
    ) -> tuple[
        AttributeCollectionEntryEntity,
        AttributeCollectionEntrySyn,
    ] | None:
        norm_to_store = {
            syn.norm: syn
            for syn in syns
        }

        if not norm_to_store:
            return None

        stmt = (
            select(
                AttributeCollectionEntry,
                AttributeCollectionEntry.norm_slot,
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
                    AttributeCollectionEntry.norm_slot.in_(
                        tuple(norm_to_store)
                    ),
                    AttributeCollectionEntryAlias.norm_alias.in_(
                        tuple(norm_to_store)
                    ),
                ),
            )
            .limit(1)
        )

        row = self.session.execute(stmt).first()

        if row is None:
            return None

        obj, entry_norm, alias_norm = row

        matched_norm = (
            entry_norm
            if entry_norm in norm_to_store
            else alias_norm
        )

        return (
            _attribute_collection_entry_model_to_entity(obj),
            norm_to_store[matched_norm],
        )


    def count_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AttributeCollectionEntry)
            .where(
                AttributeCollectionEntry.attribute_id == attribute_id
            )
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