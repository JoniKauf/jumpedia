import typing as t

from domain.typing.attribute import SlotTypeT
from domain.typing.common import ID
from domain.value_objects.field_slot import FieldSlotStr

CollectionEntryID = t.NewType("CollectionEntryID", ID)
CollectionEntryAliasID = t.NewType("CollectionEntryAliasID", ID)

type CollectionT = t.Sequence[tuple[FieldSlotStr, t.Sequence[FieldSlotStr]]]
type CollectionSlotTypeFrozenT = tuple[tuple[SlotTypeT, tuple[SlotTypeT, ...]], ...]
type CollectionFrozenT = tuple[tuple[FieldSlotStr, tuple[FieldSlotStr, ...]], ...]
