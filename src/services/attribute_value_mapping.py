import decimal
from types import MappingProxyType
import typing as t
import types as ts

from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeSlotType
from domain.value_objects.attribute import AttributeSyn
from domain.value_objects.task_value_slot import TaskValueSlot

NUMBER_MAX: t.Final[int] = 2**63 - 1
NUMBER_MIN: t.Final[int] = -NUMBER_MAX - 1
DECIMAL_PRECISION: t.Final[int] = 9  # <- adjust as needed
DECIMAL_SCALE: t.Final[decimal.Decimal] = decimal.Decimal(f"1e-{DECIMAL_PRECISION}")

def _is_number_in_range(v: int | decimal.Decimal) -> bool:
    return NUMBER_MIN <= v <= NUMBER_MAX

@dataclass(frozen=True, slots=True, eq=False)
class AttributeValueMappingService:
    def validate_and_build(self, attribute_value_mapping: t.Mapping[AttributeSyn, tuple[TaskValueSlot, ...]], syn_to_attr: t.Mapping[AttributeSyn, AttributeEntity]) -> ts.MappingProxyType[AttributeEntity, tuple[TaskValueSlot, ...]]:
        """Make sure the attribute value mapping and attribute mapping contain the same attribute types."""

        attrs_sorted = sorted(set(syn_to_attr.values()), key=lambda attr: attr.position)
        
        avm: dict[AttributeEntity, tuple[TaskValueSlot, ...]] = {}

        for attr_syn, value in attribute_value_mapping.items():
            attr = syn_to_attr[attr_syn]

            if attr in avm:
                raise ValueError("Attr mentioned more than once")
            
            avm[attr] = value

        # TODO COLLECTION!!!
        
        for attr in attrs_sorted:
            v = avm.get(attr)

            if v is None:
                if attr.slot.min_count > 0:
                    raise ValueError("Required attr missing")
                
                v = ()

            if len(v) < attr.slot.min_count:
                raise ValueError("attr min count underflow")
            
            if len(v) > attr.slot.max_count:
                raise ValueError("attr max count overflow")
            
            avm[attr] = tuple(self._validate_and_normalize_slot_with_attribute_type(slot, attr) for slot in v)

        return ts.MappingProxyType(avm)

    def _validate_and_normalize_slot_with_attribute_type(self, slot: TaskValueSlot, attr: AttributeEntity) -> TaskValueSlot:
        match attr.slot.type:
            case AttributeSlotType.STRING:
                return slot
            
            case AttributeSlotType.BOOLEAN:
                s = slot.real.value.lower()

                if s == "false":
                    return TaskValueSlot(str(False))
                if s == "true":
                    return TaskValueSlot(str(True))

                raise ValueError("Invalid Slot Str Error")

            case AttributeSlotType.INTEGER:
                try:
                    n = int(slot.real.value)
                except Exception:
                    raise ValueError("Invalid Slot Str Error")

                if not _is_number_in_range(n):
                    raise ValueError("Invalid Slot Str Error")

                return TaskValueSlot(str(n))

            case AttributeSlotType.DECIMAL:
                try:
                    n = decimal.Decimal(slot.real.value)
                except decimal.InvalidOperation:
                    raise ValueError("Invalid Slot Str Error")
                
                try:
                    n = n.quantize(DECIMAL_SCALE, rounding=decimal.ROUND_DOWN)
                except decimal.InvalidOperation:
                    raise ValueError("Invalid Slot Str Error")

                if not _is_number_in_range(n):
                    raise ValueError("Invalid Slot Str Error")

                return TaskValueSlot(format(n, "f"))

        t.assert_never(attr)
