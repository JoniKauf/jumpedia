import typing as t
from dataclasses import dataclass, field
from types import MappingProxyType

from ..attribute import AnyAttributeT, StaticAttribute, TaskAttribute, UserAttribute
from ..attribute.slot_str import SlotStr

if t.TYPE_CHECKING:
    from ..list import CommunityUser
    from ..task import Task

type AvmT[T: AnyAttributeT] = MappingProxyType[T, tuple[SlotStr, ...]]

type AnyAttributeValueMappingT = AttributeValueMapping | UserAttributeValueMapping

@dataclass(frozen=True, slots=True)
class AttributeValueMapping:
    task: Task
    static_attribute_value_mapping: AvmT[StaticAttribute]
    task_attribute_value_mapping: AvmT[TaskAttribute]

    _combined_cache: dict[StaticAttribute | TaskAttribute, tuple[SlotStr, ...]] = field(
        init=False, default_factory=dict
    )

    @property
    def combined(
        self,
    ) -> MappingProxyType[StaticAttribute | TaskAttribute, tuple[SlotStr, ...]]:
        if not self._combined_cache:
            self._combined_cache.update(self.static_attribute_value_mapping.items())
            self._combined_cache.update(self.task_attribute_value_mapping.items())

        return MappingProxyType(self._combined_cache)

    def __hash__(self) -> int:
        return hash(self.task.id)

    def __eq__(self, value: object) -> bool:
        return self.__class__ is value.__class__ and self.task.id == value.task.id  # type: ignore

@dataclass(frozen=True, slots=True)
class UserAttributeValueMapping(AttributeValueMapping):
    user_attribute_value_mapping: AvmT[UserAttribute]
    community_user: CommunityUser

    _combined_cache: dict[AnyAttributeT, tuple[SlotStr, ...]] = field(
        init=False, default_factory=dict
    )

    @property
    def combined(self) -> MappingProxyType[AnyAttributeT, tuple[SlotStr, ...]]:
        if not self._combined_cache:
            self._combined_cache.update(self.static_attribute_value_mapping.items())
            self._combined_cache.update(self.task_attribute_value_mapping.items())
            self._combined_cache.update(self.user_attribute_value_mapping.items())

        return MappingProxyType(self._combined_cache)
