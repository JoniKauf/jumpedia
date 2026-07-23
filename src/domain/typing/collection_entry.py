import typing as t

from domain.typing.attribute import SlotTypeT
from domain.typing.common import ID
from domain.value_objects.field_slot import FieldSlotStr

CollectionEntryID = t.NewType("CollectionEntryID", ID)
CollectionEntryAliasID = t.NewType("CollectionEntryAliasID", ID)


type AbstractCollectionT = t.Sequence[tuple[FieldSlotStr, t.Sequence[FieldSlotStr]]]
type FrozenCollectionT = tuple[tuple[FieldSlotStr, tuple[FieldSlotStr, ...]], ...]
type FrozenSlotTypedCollectionT = tuple[tuple[SlotTypeT, tuple[FieldSlotStr]], ...]
