from jumpedia.domain.typing.collection_entry import AbstractCollectionT
from jumpedia.domain.typing.field_mapping import RawFieldMappingT
from jumpedia.domain.value_objects.attribute import AttributeSynStr
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.string import RealStr
from jumpedia.interfaces import dsls


def collection(s: str | None) -> AbstractCollectionT:
    return (
        ()
        if s is None
        else tuple(
            (
                FieldSlotStr(k),
                tuple(FieldSlotStr(elem) for elem in v),
            )
            for k, v in dsls.mapping.engine.MappingEngine().eval(str(RealStr(s)))
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
            for k, v in dsls.mapping.engine.MappingEngine().eval(str(RealStr(s)))
        )
    )
