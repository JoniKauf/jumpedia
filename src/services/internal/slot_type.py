import decimal
import math
import typing as t
from dataclasses import dataclass

from domain.enums.attribute import AttributeSlotType
from domain.errors.business import InvalidSlotForSlotType
from domain.typing.attribute import SlotTypeT
from domain.value_objects.community import CommunityLimits
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.string import NormHash

DECIMAL_PRECISION: t.Final[int] = 9
DECIMAL_SCALE: t.Final[decimal.Decimal] = decimal.Decimal(f"1e-{DECIMAL_PRECISION}")


FALSE_SLOT: t.Final[FieldSlotStr] = FieldSlotStr("False")
TRUE_SLOT: t.Final[FieldSlotStr] = FieldSlotStr("True")

@dataclass(frozen=True, slots=True, eq=False)
class SlotTypeService:
    def single_to_slot_typed_str(
        self, slot: FieldSlotStr, type: AttributeSlotType
    ) -> FieldSlotStr:
        match type:
            case AttributeSlotType.STRING:
                return slot

            case AttributeSlotType.BOOLEAN:
                s = str(slot).lower()

                if s == "false":
                    return FALSE_SLOT
                if s == "true":
                    return TRUE_SLOT

                raise InvalidSlotForSlotType(type, slot)

            case AttributeSlotType.INTEGER:
                try:
                    n = int(str(slot))
                except Exception:
                    raise InvalidSlotForSlotType(type, slot)

                s = str(n)

                if len(s) > CommunityLimits.FIELD_SLOT_LENGTH_MAX
                    raise InvalidSlotForSlotType(type, slot)

                return FieldSlotStr(s)

            case AttributeSlotType.DECIMAL:
                try:
                    n = decimal.Decimal(str(slot))
                except decimal.InvalidOperation:
                    raise InvalidSlotForSlotType(type, slot)

                try:
                    n = n.quantize(DECIMAL_SCALE, rounding=decimal.ROUND_DOWN)
                except decimal.InvalidOperation:
                    raise InvalidSlotForSlotType(type, slot)

                if not _is_number_in_range(n):
                    raise InvalidSlotForSlotType(type, slot)

                return FieldSlotStr(format(n, "f"))

        t.assert_never(type)

    def single_to_slot_type(
        self, slot: FieldSlotStr, type: AttributeSlotType, *, validate: bool = True
    ) -> SlotTypeT:
        for s in self.many_to_slot_type((slot,), type, validate=validate):
            return s

        assert False

    def many_to_slot_type(
        self,
        slots: t.Iterable[FieldSlotStr],
        type: AttributeSlotType,
        *,
        validate: bool = True,
    ) -> t.Iterable[SlotTypeT]:
        if validate:
            slots = (self.single_to_slot_typed_str(slot, type) for slot in slots)

        match type:
            case AttributeSlotType.BOOLEAN:
                return (bool(str(slot)) for slot in slots)
            case AttributeSlotType.INTEGER:
                return (int(str(slot)) for slot in slots)
            case AttributeSlotType.DECIMAL:
                return (decimal.Decimal(str(slot)) for slot in slots)
            case AttributeSlotType.STRING:
                return (str(slot) for slot in slots)

        t.assert_never(type)

    def normalize(self, slot: SlotTypeT) -> SlotTypeT:
        if isinstance(slot, str):
            return NormHash.normalize(slot)

        return slot
