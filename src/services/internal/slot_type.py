import decimal
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeSlotType, AttributeType
from domain.types.attribute import SlotTypeT
from domain.value_objects.field_slot import FieldSlotStr

NUMBER_MAX: t.Final[int] = 2**63 - 1
NUMBER_MIN: t.Final[int] = -NUMBER_MAX - 1
DECIMAL_PRECISION: t.Final[int] = 9  # <- adjust as needed
DECIMAL_SCALE: t.Final[decimal.Decimal] = decimal.Decimal(f"1e-{DECIMAL_PRECISION}")


def _is_number_in_range(v: int | decimal.Decimal) -> bool:
    return NUMBER_MIN <= v <= NUMBER_MAX


@dataclass(frozen=True, slots=True, eq=False)
class SlotTypeService:
    def convert_to_slot_typed(
        self, slot: FieldSlotStr, type: AttributeSlotType
    ) -> FieldSlotStr:
        match type:
            case AttributeSlotType.STRING:
                return slot

            case AttributeSlotType.BOOLEAN:
                s = str(slot).lower()

                if s == "false":
                    return FieldSlotStr("False")
                if s == "true":
                    return FieldSlotStr("True")

                raise ValueError("Invalid Slot Str Error")

            case AttributeSlotType.INTEGER:
                try:
                    n = int(str(slot))
                except Exception:
                    raise ValueError("Invalid Slot Str Error")

                if not _is_number_in_range(n):
                    raise ValueError("Invalid Slot Str Error")

                return FieldSlotStr(str(n))

            case AttributeSlotType.DECIMAL:
                try:
                    n = decimal.Decimal(str(slot))
                except decimal.InvalidOperation:
                    raise ValueError("Invalid Slot Str Error")

                try:
                    n = n.quantize(DECIMAL_SCALE, rounding=decimal.ROUND_DOWN)
                except decimal.InvalidOperation:
                    raise ValueError("Invalid Slot Str Error")

                if not _is_number_in_range(n):
                    raise ValueError("Invalid Slot Str Error")

                return FieldSlotStr(format(n, "f"))

        t.assert_never(type)

    def convert_to_type(
        self, slot: FieldSlotStr, type: AttributeSlotType, *, _validate: bool = True
    ) -> SlotTypeT:
        if _validate:
            slot = self.convert_to_slot_typed(slot, type)

        match type:
            case AttributeSlotType.BOOLEAN:
                return bool(str(slot))
            case AttributeSlotType.INTEGER:
                return int(str(slot))
            case AttributeSlotType.DECIMAL:
                return decimal.Decimal(str(slot))
            case AttributeSlotType.STRING:
                return str(slot)

        t.assert_never(type)
