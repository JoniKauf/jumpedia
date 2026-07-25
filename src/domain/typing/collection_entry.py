import typing as t

lazy from domain.typing.attribute import SlotTypeT
lazy from domain.typing.common import ID
lazy from domain.value_objects.field_slot import FieldSlotStr

CollectionEntryID = t.NewType("CollectionEntryID", ID)
CollectionEntryAliasID = t.NewType("CollectionEntryAliasID", ID)


type AbstractCollectionT = t.Sequence[tuple[FieldSlotStr, t.Sequence[FieldSlotStr]]]
type FrozenCollectionT = tuple[tuple[FieldSlotStr, tuple[FieldSlotStr, ...]], ...]
type FrozenSlotTypedCollectionT = tuple[tuple[SlotTypeT, tuple[FieldSlotStr]], ...]
