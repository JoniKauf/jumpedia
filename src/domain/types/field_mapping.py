import typing as t

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AnyAttributeTypeT, AttributeID, SlotTypeT
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr

# We don't use a dict here but rather key-value tuples since the mapping dsl
# is designed to return simple data (no domain specific types like AttributeSynStr).
# That means we COULD make it return a dict, but then if a key exactly matches, we
# would get an error, while we would get a different error if the keys match when
# normalized (with AttributeSynStr) wayyy later. To have this all occur in one place,
# the DSL guarantees no key uniqueness and lets us do the work when building a field
# mapping.
type FieldMappingRawT = t.Sequence[tuple[AttributeSynStr, t.Sequence[FieldSlotStr]]]

type FieldMappingEntityT[T: AttributeType = AnyAttributeTypeT] = t.Mapping[
    AttributeEntity[T], t.Sequence[FieldSlotStr]
]
type FieldMappingEntityFrozenT[T: AttributeType = AnyAttributeTypeT] = frozendict[
    AttributeEntity[T], tuple[FieldSlotStr, ...]
]

type FieldMappingIDT = t.Mapping[AttributeID, t.Sequence[FieldSlotStr]]
type FieldMappingIDMutT = dict[AttributeID, tuple[FieldSlotStr, ...]]
type FieldMappingIDFrozenT = frozendict[AttributeID, tuple[FieldSlotStr, ...]]

type FieldMappingIDSlotTypeT = t.Mapping[AttributeID, tuple[SlotTypeT, ...]]