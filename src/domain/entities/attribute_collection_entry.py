from domain.entities.base import BaseEntity
from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.value_objects.attribute_collection_entry import \
    AttributeCollectionEntrySyn


class AttributeCollectionEntryEntity(BaseEntity[AttributeCollectionEntryID]):
    def __init__(
        self,
        id: AttributeCollectionEntryID,
        attribute_id: AttributeID,
        name: AttributeCollectionEntrySyn,
    ) -> None:
        super().__init__(id)
        self._attribute_id = attribute_id
        self.name = name

    @property
    def attribute_id(self) -> AttributeID:
        return self._attribute_id

    @property
    def name(self) -> AttributeCollectionEntrySyn:
        return self._name

    @name.setter
    def name(self, value: AttributeCollectionEntrySyn) -> None:
        self._name = value
