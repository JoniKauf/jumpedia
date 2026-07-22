import typing as t

from domain.typing.attribute import SlotTypeT
from domain.value_objects.field_slot import FieldSlotStr


class AbstractCollectionEntry(t.NamedTuple):
    value: FieldSlotStr
    aliases: t.Sequence[FieldSlotStr]

class FrozenCollectionEntry(t.NamedTuple):
    value: FieldSlotStr
    aliases: tuple[FieldSlotStr, ...]

class FrozenSlotTypedCollectionEntry(t.NamedTuple):
    value: SlotTypeT
    aliases: tuple[FieldSlotStr, ...]