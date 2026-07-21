from domain.entities.base import BaseEntity
from domain.typing.attribute import AttributeID
from domain.typing.collection_entry import CollectionEntryID
from domain.value_objects.field_slot import FieldSlotStr


class CollectionEntryEntity(BaseEntity[CollectionEntryID]):
    def __init__(
        self,
        collection_entry_id: CollectionEntryID,
        attribute_id: AttributeID,
        value: FieldSlotStr,
    ) -> None:
        super().__init__(collection_entry_id)
        self._attribute_id = attribute_id
        self.value = value

    @property
    def collection_entry_id(self) -> CollectionEntryID:
        return self._composite_key[0]

    @property
    def attribute_id(self) -> AttributeID:
        return self._attribute_id

    @property
    def value(self) -> FieldSlotStr:
        return self._value

    @value.setter
    def value(self, value: FieldSlotStr) -> None:
        self._value = value
