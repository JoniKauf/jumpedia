from domain.types.collection_entry import CollectionT
from domain.types.field_mapping import FieldMappingRawT
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from interfaces import dsls


def collection(s: str | None) -> CollectionT:
    return (
        ()
        if s is None
        else tuple(
            (
                FieldSlotStr(k),
                tuple(FieldSlotStr(elem) for elem in v),
            )
            for k, v in dsls.mapping.engine.MappingEngine().eval(s)
        )
    )


def field_mapping(
    s: str | None,
) -> FieldMappingRawT:
    return tuple(
        ()
        if s is None
        else tuple(
            (AttributeSynStr(k), tuple(FieldSlotStr(slot) for slot in v))
            for k, v in dsls.mapping.engine.MappingEngine().eval(s)
        )
    )
