from domain.typing.collection_entry import AbstractCollectionEntry, AbstractCollectionT
from domain.typing.field_mapping import RawFieldMappingT
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from interfaces import dsls


def collection(s: str | None) -> AbstractCollectionT:
    return (
        ()
        if s is None
        else tuple(
            AbstractCollectionEntry(
                FieldSlotStr(k),
                tuple(FieldSlotStr(elem) for elem in v),
            )
            for k, v in dsls.mapping.engine.MappingEngine().eval(s)
        )
    )


def field_mapping(
    s: str | None,
) -> RawFieldMappingT:
    return tuple(
        ()
        if s is None
        else tuple(
            (AttributeSynStr(k), tuple(FieldSlotStr(slot) for slot in v))
            for k, v in dsls.mapping.engine.MappingEngine().eval(s)
        )
    )
