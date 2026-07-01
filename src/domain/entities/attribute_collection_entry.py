from domain.entities.base import BaseEntity
from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr


class AttributeCollectionEntryEntity(BaseEntity[AttributeCollectionEntryID]):
    def __init__(
        self,
        attribute_collection_entry_id: AttributeCollectionEntryID,
        attribute_id: AttributeID,
        value: TaskAttributeSlotStr,
    ) -> None:
        super().__init__(attribute_collection_entry_id)
        self._attribute_id = attribute_id
        self.value = value

    @property
    def attribute_collection_entry_id(self) -> AttributeCollectionEntryID:
        return self._composite_key[0]

    @property
    def attribute_id(self) -> AttributeID:
        return self._attribute_id

    @property
    def value(self) -> TaskAttributeSlotStr:
        return self._value

    @value.setter
    def value(self, value: TaskAttributeSlotStr) -> None:
        self._value = value
