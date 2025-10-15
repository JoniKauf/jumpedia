
from dataclasses import dataclass, field
from types import MappingProxyType
from structures.attribute.static_attribute import StaticAttribute

from structures.attribute import AnyAttributeT
from structures.attribute.slot_type import TypeStr
from structures.attribute.task_attribute import TaskAttribute
from structures.attribute.user_attribute import UserAttribute
import typing as t

if t.TYPE_CHECKING:
    from structures.task import Task

type AvmT[T: AnyAttributeT] = MappingProxyType[T, tuple[TypeStr, ...]]

@dataclass(frozen=True, slots=True)
class AttributeValueMapping():
    task: Task
    static_attribute_value_mapping: AvmT[StaticAttribute] = field(default_factory=lambda: MappingProxyType({}))
    task_attribute_value_mapping: AvmT[TaskAttribute] = field(default_factory=lambda: MappingProxyType({}))
    user_attribute_value_mapping: AvmT[UserAttribute] = field(default_factory=lambda: MappingProxyType({}))

    _combined_cache: dict[AnyAttributeT, tuple[TypeStr, ...]] = field(init=False, default_factory=dict)
    
    @property
    def combined_attribute_value_mapping(self) -> AvmT[AnyAttributeT]:
        if not self._combined_cache:
            self._combined_cache.update(
                self.static_attribute_value_mapping |
                self.task_attribute_value_mapping |
                self.user_attribute_value_mapping
            )

        return MappingProxyType(self._combined_cache)