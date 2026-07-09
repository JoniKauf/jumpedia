import typing as t

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr

type FieldMappingRawT = t.Mapping[AttributeSynStr, t.Sequence[FieldSlotStr]]

type FieldMappingEntityT[T: AttributeType = AttributeType.AllT] = t.Mapping[
    AttributeEntity[T], t.Sequence[FieldSlotStr]
]
type FieldMappingEntityFrozenT[T: AttributeType = AttributeType.AllT] = frozendict[
    AttributeEntity[T], tuple[FieldSlotStr, ...]
]

type FieldMappingIDT = t.Mapping[AttributeID, t.Sequence[FieldSlotStr]]
type FieldMappingIDFrozenT = frozendict[AttributeID, tuple[FieldSlotStr, ...]]
