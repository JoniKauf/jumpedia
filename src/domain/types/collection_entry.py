import typing as t

from domain.types.common import ID
from domain.value_objects.field_slot import FieldSlotStr

CollectionEntryID = t.NewType("CollectionEntryID", ID)
CollectionEntryAliasID = t.NewType("CollectionEntryAliasID", ID)

type CollectionT = t.Sequence[tuple[FieldSlotStr, t.Sequence[FieldSlotStr]]]
type FrozenCollectionT = tuple[tuple[FieldSlotStr, tuple[FieldSlotStr, ...]], ...]