import typing as t

lazy from domain.entities.attribute import AttributeEntity
lazy from domain.enums.attribute import AttributeType
lazy from domain.typing.attribute import AnyAttributeTypeT, AttributeID, SlotTypeT
lazy from domain.value_objects.attribute import AttributeSynStr
lazy from domain.value_objects.field_slot import FieldSlotStr

# We don't use a dict here but rather key-value tuples since the mapping dsl
# is designed to return simple data (no domain specific types like AttributeSynStr).
# That means we COULD make it return a dict, but then if a key exactly matches, we
# would get an error, while we would get a different error if the keys match when
# normalized (with AttributeSynStr) wayyy later. To have this all occur in one place,
# the DSL guarantees no key uniqueness and lets us do the work when building a field
# mapping.
type RawFieldMappingT = t.Sequence[tuple[AttributeSynStr, t.Sequence[FieldSlotStr]]]

type FrozenFieldMappingEntityToStrings[
    T: AttributeType = AnyAttributeTypeT
] = frozendict[AttributeEntity[T], tuple[FieldSlotStr, ...]]

type AbstractFieldMappingIDToStringsT = t.Mapping[AttributeID, t.Sequence[FieldSlotStr]]
type MutableFieldMappingIDToStringsT = dict[AttributeID, tuple[FieldSlotStr, ...]]
type FrozenFieldMappingIDToStringsT = frozendict[AttributeID, tuple[FieldSlotStr, ...]]

type AbstractFieldMappingIDToSlotTypeT = t.Mapping[AttributeID, tuple[SlotTypeT, ...]]
type FrozenFieldMappingEntityToSlotTypeT = frozendict[
    AttributeEntity, tuple[SlotTypeT, ...]
]
