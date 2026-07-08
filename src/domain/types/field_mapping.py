import typing as t

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeType
from domain.types.attribute import AttributeID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr


type RawFieldMappingT = t.Mapping[AttributeSynStr, t.Sequence[FieldSlotStr]]

type EntityFieldMappingT[T: AttributeType = AttributeType.AllT] = t.Mapping[AttributeEntity[T], t.Sequence[FieldSlotStr]]
type EntityFrozenFieldMappingT[T: AttributeType = AttributeType.AllT] = frozendict[AttributeEntity[T], tuple[FieldSlotStr, ...]]

type IDFieldMappingT = t.Mapping[AttributeID, t.Sequence[FieldSlotStr]]
type IDFrozenFieldMappingT = frozendict[AttributeID, tuple[FieldSlotStr, ...]]