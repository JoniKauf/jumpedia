import itertools
import types as ts
import typing as t

from sqlalchemy import delete, func, or_, select

from db.models import AttributeModel, CollectionEntryAliasModel, CollectionEntryModel
from domain.entities.collection_entry import CollectionEntryEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.errors import business
from domain.typing.attribute import (
    AttributeID,
    NoneKindedAttributeT,
    NonStaticAttributeTypeT,
)
from domain.typing.collection_entry import (
    CollectionEntryID,
    CollectionFrozenT,
    CollectionT,
)
from domain.typing.list import ListID
from domain.value_objects.field_slot import FieldSlotStr
from repositories.base import BaseRepository


def collection_entry_model_to_entity(
    model: CollectionEntryModel,
) -> CollectionEntryEntity:
    return CollectionEntryEntity(
        model.collection_entry_id,
        model.attribute_id,
        FieldSlotStr._create_from_real_and_norm(model.real_value, model.norm_value),
    )


class CollectionEntryRepository(BaseRepository):
    def create_collection(
        self,
        attribute_id: AttributeID,
        collection: CollectionT,
    ) -> None:
        entry_objs = tuple(
            CollectionEntryModel(
                attribute_id=attribute_id,
                index=i,
                norm_value=value.norm,
                real_value=value.real,
            )
            for i, (value, _) in enumerate(collection)
        )

        if not entry_objs:
            return

        self._session.add_all(entry_objs)
        self._session.flush()  # For collection_entry_id update

        alias_objs = tuple(
            CollectionEntryAliasModel(
                collection_entry_id=entry_obj.collection_entry_id,
                index=j,
                attribute_id=attribute_id,
                norm_alias=alias.norm,
                real_alias=alias.real,
            )
            for entry_obj, (_, aliases) in zip(entry_objs, collection, strict=True)
            for j, alias in enumerate(aliases)
        )

        if alias_objs:
            self._session.add_all(alias_objs)

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
            raise business.NotFoundById(CollectionEntryEntity)

        self._session.delete(obj)
        self._session.flush()

    def get_collection_by_attribute_id(
        self,
        attribute_id: AttributeID,
    ) -> CollectionFrozenT:
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
                    FieldSlotStr._create_from_real_and_norm(
                        alias_obj.real_alias,
                        alias_obj.norm_alias,
                    )
                )

        return tuple(
            (entry.value, tuple(entry_aliases.get(entry.collection_entry_id, ())))
            for entry in ordered
        )

    def get_grouped_collections_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
        kinds: t.AbstractSet[t.Literal[AttributeKind.NONE]],
    ) -> frozendict[AttributeID, CollectionFrozenT]:
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
                AttributeModel.kind.in_(kinds),
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
                    FieldSlotStr._create_from_real_and_norm(
                        alias_obj.real_alias,
                        alias_obj.norm_alias,
                    )
                )

        return frozendict(
            {
                attribute_id: tuple(
                    (
                        entry.value,
                        tuple(entry_aliases.get(entry.collection_entry_id, ())),
                    )
                    for entry in collection
                )
                for attribute_id, collection in grouped_entries.items()
            }
        )

    def get_grouped_value_to_index_by_list_id(
        self,
        list_id: ListID,
        types: t.AbstractSet[AttributeType],
        kinds: t.AbstractSet[NoneKindedAttributeT],
    ) -> frozendict[AttributeID, frozendict[FieldSlotStr, int]]:
        stmt = (
            select(CollectionEntryModel)
            .join(
                AttributeModel,
                AttributeModel.attribute_id == CollectionEntryModel.attribute_id,
            )
            .where(
                AttributeModel.list_id == list_id,
                AttributeModel.type.in_(types),
                AttributeModel.kind.in_(kinds),
            )
            .order_by(
                CollectionEntryModel.attribute_id.asc(),
                CollectionEntryModel.index.asc(),
            )
        )

        return frozendict(
            (
                attribute_id,
                frozendict(
                    (
                        FieldSlotStr._create_from_real_and_norm(
                            obj.real_value,
                            obj.norm_value,
                        ),
                        obj.index,
                    )
                    for obj in group
                ),
            )
            for attribute_id, group in itertools.groupby(
                self._session.scalars(stmt),
                lambda obj: obj.attribute_id,
            )
        )

    def replace_collection(
        self, attribute_id: AttributeID, collection: CollectionT
    ) -> None:
        """Replaces the entire collection of an attribute. Preserves entry order."""

        self._session.execute(
            delete(CollectionEntryModel).where(
                CollectionEntryModel.attribute_id == attribute_id,
            )
        )

        self.create_collection(attribute_id, collection)
