import types as ts
import typing as t

from sqlalchemy import func, or_, select

from db.models import (
    CollectionEntryAliasModel,
    CollectionEntryModel,
    AttributeModel,
)
from domain import errors
from domain.entities.collection_entry import CollectionEntryEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.types.collection_entry import CollectionEntryID
from domain.types.list import ListID
from domain.value_objects.field_slot import FieldSlotStr
from repositories.base import BaseRepository
from repositories.dtos.collection_entry import (
    CollectionEntryAliasInsert,
    CollectionEntryEntityWithAliases,
    CollectionEntryInsert,
)


def collection_entry_model_to_entity(
    model: CollectionEntryModel,
) -> CollectionEntryEntity:
    return CollectionEntryEntity(
        model.collection_entry_id,
        model.attribute_id,
        FieldSlotStr(_real=model.real_value, _norm=model.norm_value),
    )


class CollectionEntryRepository(BaseRepository):
    def create_many(
        self, entries: t.Iterable[CollectionEntryInsert]
    ) -> tuple[CollectionEntryEntity, ...]:
        """Preserves order."""
        objs = tuple(
            CollectionEntryModel(
                attribute_id=entry.attribute_id,
                index=entry.index.value,
                norm_value=entry.value.norm,
                real_value=entry.value.real,
            )
            for entry in entries
        )

        self._session.add_all(objs)
        self._session.flush()

        return tuple(collection_entry_model_to_entity(obj) for obj in objs)

    def create_many_aliases(
        self, entry_aliases: t.Iterable[CollectionEntryAliasInsert]
    ) -> None:
        objs = tuple(
            CollectionEntryAliasModel(
                attribute_id=entry_alias.attribute_id,
                index=entry_alias.index.value,
                norm_alias=entry_alias.alias.norm,
                real_alias=entry_alias.alias.real,
            )
            for entry_alias in entry_aliases
        )

        self._session.add_all(objs)
        self._session.flush()

    def get_by_id(
        self,
        entry_id: CollectionEntryID,
    ) -> CollectionEntryEntity | None:
        obj = self._session.get(CollectionEntryModel, entry_id)

        return None if obj is None else collection_entry_model_to_entity(obj)

    def get_all_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> tuple[CollectionEntryEntity, ...]:
        stmt = (
            select(CollectionEntryModel)
            .where(CollectionEntryModel.attribute_id == attribute_id)
            .order_by(CollectionEntryModel.index.asc())
        )

        return tuple(
            collection_entry_model_to_entity(obj) for obj in self._session.scalars(stmt)
        )

    def get_by_attribute_id_and_name(
        self,
        attribute_id: AttributeID,
        name: FieldSlotStr,
    ) -> CollectionEntryEntity | None:
        stmt = select(CollectionEntryModel).where(
            CollectionEntryModel.attribute_id == attribute_id,
            CollectionEntryModel.norm_value == name.norm,
        )

        obj = self._session.scalar(stmt)

        return None if obj is None else collection_entry_model_to_entity(obj)

    def get_by_attribute_id_and_any_syn(
        self,
        attribute_id: AttributeID,
        syns: t.Iterable[FieldSlotStr],
    ) -> (
        tuple[
            CollectionEntryEntity,
            FieldSlotStr,
        ]
        | None
    ):
        norm_to_store = {syn.norm: syn for syn in syns}

        if not norm_to_store:
            return None

        stmt = (
            select(
                CollectionEntryModel,
                CollectionEntryModel.norm_value,
                CollectionEntryAliasModel.norm_alias,
            )
            .outerjoin(
                CollectionEntryAliasModel,
                CollectionEntryAliasModel.collection_entry_id
                == CollectionEntryModel.collection_entry_id,
            )
            .where(
                CollectionEntryModel.attribute_id == attribute_id,
                or_(
                    CollectionEntryModel.norm_value.in_(tuple(norm_to_store)),
                    CollectionEntryAliasModel.norm_alias.in_(tuple(norm_to_store)),
                ),
            )
            .limit(1)
        )

        row = self._session.execute(stmt).first()

        if row is None:
            return None

        obj, entry_norm, alias_norm = row

        matched_norm = entry_norm if entry_norm in norm_to_store else alias_norm

        return (
            collection_entry_model_to_entity(obj),
            norm_to_store[matched_norm],
        )

    def count_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(CollectionEntryModel)
            .where(CollectionEntryModel.attribute_id == attribute_id)
        )

        return self._session.scalar(stmt) or 0

    def delete(
        self,
        entry_id: CollectionEntryID,
    ) -> None:
        obj = self._session.get(
            CollectionEntryModel,
            entry_id,
        )

        if obj is None:
            raise errors.NotFoundById(CollectionEntryEntity)

        self._session.delete(obj)
        self._session.flush()

    def get_collection_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> tuple[CollectionEntryEntityWithAliases, ...]:
        stmt = (
            select(
                CollectionEntryModel,
                CollectionEntryAliasModel,
            )
            .outerjoin(
                CollectionEntryAliasModel,
                CollectionEntryAliasModel.collection_entry_id
                == CollectionEntryModel.collection_entry_id,
            )
            .where(
                CollectionEntryModel.attribute_id == attribute_id,
            )
            .order_by(
                CollectionEntryModel.index.asc(),
                CollectionEntryAliasModel.index.asc(),
            )
        )

        entries: dict[
            CollectionEntryID,
            CollectionEntryEntity,
        ] = {}
        entry_aliases: dict[
            CollectionEntryID,
            list[FieldSlotStr],
        ] = {}

        ordered: list[CollectionEntryEntity] = []

        for entry_obj, alias_obj in self._session.execute(stmt):
            entry_obj: CollectionEntryModel
            alias_obj: CollectionEntryAliasModel | None

            entry = entries.get(entry_obj.collection_entry_id)

            if entry is None:
                entry = collection_entry_model_to_entity(entry_obj)
                entries[entry.collection_entry_id] = entry
                ordered.append(entry)

            if alias_obj is not None:
                entry_aliases.setdefault(entry.collection_entry_id, []).append(
                    FieldSlotStr(
                        _real=alias_obj.real_alias,
                        _norm=alias_obj.norm_alias,
                    )
                )

        return tuple(
            CollectionEntryEntityWithAliases(
                entry=entry,
                aliases=tuple(entry_aliases.get(entry.collection_entry_id, ())),
            )
            for entry in ordered
        )

    def get_grouped_collections_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
    ) -> ts.MappingProxyType[AttributeID, tuple[CollectionEntryEntityWithAliases, ...]]:
        stmt = (
            select(CollectionEntryModel, CollectionEntryAliasModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == CollectionEntryModel.attribute_id,
            )
            .outerjoin(
                CollectionEntryAliasModel,
                CollectionEntryAliasModel.collection_entry_id
                == CollectionEntryModel.collection_entry_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.type.in_(types),
            )
            .order_by(
                CollectionEntryModel.attribute_id.asc(),
                CollectionEntryModel.index.asc(),
                CollectionEntryAliasModel.index.asc(),
            )
        )

        entries: dict[CollectionEntryID, CollectionEntryEntity] = {}
        entry_aliases: dict[
            CollectionEntryID,
            list[FieldSlotStr],
        ] = {}
        grouped_entries: dict[
            AttributeID,
            list[CollectionEntryEntity],
        ] = {}

        for entry_obj, alias_obj in self._session.execute(stmt):
            entry_obj: CollectionEntryModel
            alias_obj: CollectionEntryAliasModel | None

            entry = entries.get(entry_obj.collection_entry_id)

            if entry is None:
                entry = collection_entry_model_to_entity(entry_obj)
                entries[entry.collection_entry_id] = entry
                grouped_entries.setdefault(entry.attribute_id, []).append(entry)

            if alias_obj is not None:
                entry_aliases.setdefault(entry.collection_entry_id, []).append(
                    FieldSlotStr(
                        _real=alias_obj.real_alias,
                        _norm=alias_obj.norm_alias,
                    )
                )

        return ts.MappingProxyType(
            {
                attribute_id: tuple(
                    CollectionEntryEntityWithAliases(
                        entry=entry,
                        aliases=tuple(entry_aliases.get(entry.collection_entry_id, ())),
                    )
                    for entry in collection
                )
                for attribute_id, collection in grouped_entries.items()
            }
        )
