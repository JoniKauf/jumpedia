import decimal
import types as ts
import typing as t
from dataclasses import dataclass
from types import MappingProxyType

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.enums.attribute import AttributeSlotType
from domain.types.attribute import AttributeID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr
from repositories.attribute_collection_entry import AttributeCollectionEntryRepository
from repositories.dtos.attribute_collection_entry import (
    AttributeCollectionEntryEntityWithAliases,
)

NUMBER_MAX: t.Final[int] = 2**63 - 1
NUMBER_MIN: t.Final[int] = -NUMBER_MAX - 1
DECIMAL_PRECISION: t.Final[int] = 9  # <- adjust as needed
DECIMAL_SCALE: t.Final[decimal.Decimal] = decimal.Decimal(f"1e-{DECIMAL_PRECISION}")


def _is_number_in_range(v: int | decimal.Decimal) -> bool:
    return NUMBER_MIN <= v <= NUMBER_MAX


@dataclass(frozen=True, slots=True, eq=False)
class AttributeValueMappingService:
    def validate_and_build(
        self,
        attribute_value_mapping: t.Mapping[
            AttributeSynStr, t.Sequence[TaskAttributeSlotStr]
        ],
        syn_to_attr: t.Mapping[AttributeSynStr, AttributeEntity],
        attribute_id_to_collection: t.Mapping[
            AttributeID, t.Sequence[AttributeCollectionEntryEntityWithAliases]
        ],
    ) -> ts.MappingProxyType[AttributeEntity, tuple[TaskAttributeSlotStr, ...]]:
        """Make sure the attribute value mapping and attribute mapping contain the same attribute types."""

        attrs_sorted = sorted(
            set(syn_to_attr.values()), key=lambda attr: attr.position.value
        )

        avm: dict[AttributeEntity, tuple[TaskAttributeSlotStr, ...]] = {}

        for attr_syn, value in attribute_value_mapping.items():
            attr = syn_to_attr[attr_syn]

            if attr in avm:
                raise ValueError("Attr mentioned more than once")

            avm[attr] = tuple(value)

        for attr in attrs_sorted:
            v: tuple[TaskAttributeSlotStr, ...] | None = avm.get(attr)

            if v is None:
                if attr.slot.min_count > 0:
                    raise ValueError("Required attr missing")

                v = ()

            if len(v) < attr.slot.min_count:
                raise ValueError("attr min count underflow")

            if len(v) > attr.slot.max_count:
                raise ValueError("attr max count overflow")

            v = tuple(
                self._validate_and_normalize_slot_with_attribute_type(slot, attr)
                for slot in v
            )

            collection = attribute_id_to_collection.get(attr.attribute_id)

            # Not None or empty
            if collection:
                syn_to_value: dict[TaskAttributeSlotStr, TaskAttributeSlotStr] = {
                    syn: entry_with_aliases.entry.value
                    for entry_with_aliases in collection
                    for syn in (
                        entry_with_aliases.entry.value,
                        *entry_with_aliases.aliases,
                    )
                }

                collectionified_v: list[TaskAttributeSlotStr] = []

                for slot in v:
                    slot = syn_to_value.get(slot)

                    if slot is None:
                        raise ValueError("Unknown slot")

                    collectionified_v.append(slot)

                v = tuple(collectionified_v)

            avm[attr] = v

        return ts.MappingProxyType(avm)

    def _validate_and_normalize_slot_with_attribute_type(
        self, slot: TaskAttributeSlotStr, attr: AttributeEntity
    ) -> TaskAttributeSlotStr:
        match attr.slot.type:
            case AttributeSlotType.STRING:
                return slot

            case AttributeSlotType.BOOLEAN:
                s = slot.real.value.lower()

                if s == "false":
                    return TaskAttributeSlotStr("False")
                if s == "true":
                    return TaskAttributeSlotStr("True")

                raise ValueError("Invalid Slot Str Error")

            case AttributeSlotType.INTEGER:
                try:
                    n = int(slot.real.value)
                except Exception:
                    raise ValueError("Invalid Slot Str Error")

                if not _is_number_in_range(n):
                    raise ValueError("Invalid Slot Str Error")

                return TaskAttributeSlotStr(str(n))

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

                return TaskAttributeSlotStr(format(n, "f"))

        t.assert_never(attr)
