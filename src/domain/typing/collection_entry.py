import typing as t

from domain.typing.common import ID
from domain.value_objects.collection_entry import AbstractCollectionEntry, FrozenCollectionEntry, FrozenSlotTypedCollectionEntry

CollectionEntryID = t.NewType("CollectionEntryID", ID)
CollectionEntryAliasID = t.NewType("CollectionEntryAliasID", ID)


type AbstractCollectionT = t.Sequence[AbstractCollectionEntry]
type FrozenCollectionT = tuple[FrozenCollectionEntry, ...]
type FrozenSlotTypedCollectionT = tuple[FrozenSlotTypedCollectionEntry, ...]
