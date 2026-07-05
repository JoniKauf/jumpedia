import decimal
import types as ts
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeSlotType, AttributeType
from domain.types.attribute import AttributeID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from repositories.dtos.collection_entry import CollectionEntryEntityWithAliases

NUMBER_MAX: t.Final[int] = 2**63 - 1
NUMBER_MIN: t.Final[int] = -NUMBER_MAX - 1
DECIMAL_PRECISION: t.Final[int] = 9  # <- adjust as needed
DECIMAL_SCALE: t.Final[decimal.Decimal] = decimal.Decimal(f"1e-{DECIMAL_PRECISION}")


def _is_number_in_range(v: int | decimal.Decimal) -> bool:
    return NUMBER_MIN <= v <= NUMBER_MAX


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingService:
    def validate_and_build[T: AttributeType](
        self,
        field_mapping: t.Mapping[AttributeSynStr, t.Sequence[FieldSlotStr]],
        syn_to_attr: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[
            AttributeID, t.Sequence[CollectionEntryEntityWithAliases]
        ],
    ) -> ts.MappingProxyType[AttributeEntity[T], tuple[FieldSlotStr, ...]]:
        attrs_sorted = sorted(
            set(syn_to_attr.values()), key=lambda attr: attr.position.value
        )

        avm: dict[AttributeEntity[T], tuple[FieldSlotStr, ...]] = {}

        for attr_syn, value in field_mapping.items():
            attr = syn_to_attr[attr_syn]

            if attr in avm:
                raise ValueError("Attr mentioned more than once")

            avm[attr] = tuple(value)

        for attr in attrs_sorted:
            v: tuple[FieldSlotStr, ...] | None = avm.get(attr)

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

            collection = attr_id_to_collection.get(attr.attribute_id)

            # Not None or empty
            if collection:
                syn_to_value: dict[FieldSlotStr, FieldSlotStr] = {
                    syn: entry_with_aliases.entry.value
                    for entry_with_aliases in collection
                    for syn in (
                        entry_with_aliases.entry.value,
                        *entry_with_aliases.aliases,
                    )
                }

                collectionified_v: list[FieldSlotStr] = []

                for slot in v:
                    slot = syn_to_value.get(slot)

                    if slot is None:
                        raise ValueError("Unknown slot")

                    collectionified_v.append(slot)

                v = tuple(collectionified_v)

            avm[attr] = v

        return ts.MappingProxyType(avm)

    def _validate_and_normalize_slot_with_attribute_type(
        self, slot: FieldSlotStr, attr: AttributeEntity
    ) -> FieldSlotStr:
        match attr.slot.type:
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

        t.assert_never(attr)
