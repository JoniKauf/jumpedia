from dataclasses import dataclass

from jumpedia.domain.entities.base import BaseEntity

lazy from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.collection_entry import CollectionEntryID

lazy from jumpedia.domain.value_objects.field_slot import FieldSlotStr


@dataclass(frozen=True, slots=True)
class CollectionEntryEntity(BaseEntity[CollectionEntryID]):
    attribute_id: AttributeID
    value: FieldSlotStr

    @property
    def collection_entry_id(self) -> CollectionEntryID:
        return self.key[0]
