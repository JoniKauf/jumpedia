from dataclasses import dataclass

from domain.value_objects.attribute_collection_entry import AttributeCollectionEntrySyn


@dataclass(frozen=True, slots=True)
class CreateAttributeCollectionEntry:
    value: AttributeCollectionEntrySyn
    aliases: tuple[AttributeCollectionEntrySyn, ...]
