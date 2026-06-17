


from dataclasses import dataclass

from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.value_objects.attribute_collection_entry import AttributeCollectionEntrySyn


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryInsert:
    attribute_id: AttributeID
    index: int
    value: AttributeCollectionEntrySyn


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryAliasInsert:
    attribute_collection_entry_id: AttributeCollectionEntryID
    attribute_id: AttributeID
    alias: AttributeCollectionEntrySyn