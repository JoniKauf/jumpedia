import decimal
import types as ts
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeType
from domain.enums.edit_mode import FieldMappingEditMode
from domain.types.attribute import AttributeID
from domain.types.collection_entry import CollectionT
from domain.types.field_mapping import EntityFieldMappingT, EntityFrozenFieldMappingT, IDFieldMappingT, RawFieldMappingT
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from repositories.field_slot import FieldSlotRepository
from services.internal.edit_mode import EditModeService
from services.internal.slot_type import SlotTypeService


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingService:
    _slot_type_service: SlotTypeService
    _edit_mode_service: EditModeService

    def build_raw[T: AttributeType](
        self,
        field_mapping: RawFieldMappingT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[
            AttributeID, CollectionT
        ],
    ) -> EntityFrozenFieldMappingT[T]:
        unchecked_field_mapping = self._try_convert_syns_to_attr_ids(field_mapping, syn_to_attribute)

        return self.build(unchecked_field_mapping, frozenset(syn_to_attribute.values()), attr_id_to_collection)

    def _try_convert_syns_to_attr_ids(self, field_mapping: RawFieldMappingT, syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity]) -> IDFieldMappingT:
        unchecked_field_mapping: IDFieldMappingT = {}

        for attr_syn, value in field_mapping.items():
            attr = syn_to_attribute[attr_syn]

            if attr in unchecked_field_mapping:
                raise ValueError("Attr mentioned more than once")

            unchecked_field_mapping[attr.attribute_id] = tuple(value)

        return unchecked_field_mapping

    def build[T: AttributeType](
        self, 
        unchecked_field_mapping: IDFieldMappingT,
        attributes: t.AbstractSet[AttributeEntity[T]], 
        attr_id_to_collection: t.Mapping[
            AttributeID, CollectionT
        ], 
    ) -> EntityFrozenFieldMappingT[T]:
        res: dict[AttributeEntity[T], tuple[FieldSlotStr, ...]] = {}

        for attr in attributes:
            v = unchecked_field_mapping.get(attr.attribute_id)

            if v is None:
                if attr.slot.min_count > 0:
                    raise ValueError("Required attr missing")

                v = ()

            if len(v) < attr.slot.min_count:
                raise ValueError("attr min count underflow")

            if len(v) > attr.slot.max_count:
                raise ValueError("attr max count overflow")

            v = tuple(
                self._slot_type_service.convert_to_slot_typed(slot, attr.slot.type)
                for slot in v
            )

            collection = attr_id_to_collection.get(attr.attribute_id)

            # Not None or empty
            if collection:
                syn_to_value: dict[FieldSlotStr, FieldSlotStr] = {
                    syn: entry_with_aliases[0]
                    for entry_with_aliases in collection
                    for syn in (
                        entry_with_aliases[0],
                        *entry_with_aliases[1],
                    )
                }

                collectionified_v: list[FieldSlotStr] = []

                for slot in v:
                    slot = syn_to_value.get(slot)

                    if slot is None:
                        raise ValueError("Unknown slot")

                    collectionified_v.append(slot)

                v = tuple(collectionified_v)

            res[attr] = v

        return frozendict(res)

    def build_edit[T: AttributeType](self, edit_mode: FieldMappingEditMode, current_field_mapping: IDFieldMappingT, new_field_mapping: RawFieldMappingT, syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]], attribute_id_to_collection: t.Mapping[AttributeID, CollectionT]) -> EntityFrozenFieldMappingT[T]:
        # Build the new mapping to see if even valid on its own
        new_fm = {attr.attribute_id: v for attr, v in self.build_raw(new_field_mapping, syn_to_attribute, attribute_id_to_collection).items()}
        
        del new_field_mapping

        # Edit the new mapping with the current
        new_fm = self._edit_mode_service.handle_field_mapping_edit(edit_mode, current_field_mapping, new_fm)

        del current_field_mapping

        # Rebuild combined mapping to see if end result is valid
        return self.build(new_fm, frozenset(syn_to_attribute.values()), attribute_id_to_collection)