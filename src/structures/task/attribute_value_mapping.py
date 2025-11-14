import typing as t
from dataclasses import dataclass, field
from types import MappingProxyType

from ..attribute import AnyAttributeT, StaticAttribute, TaskAttribute, UserAttribute
from ..attribute.slot_str import SlotStr

if t.TYPE_CHECKING:
    from ..list import CommunityUser
    from ..task import Task

type AvmT[T: AnyAttributeT] = MappingProxyType[T, tuple[SlotStr, ...]]


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


@dataclass(frozen=True, slots=True)
class UserAttributeValueMapping:
    attribute_value_mapping: AttributeValueMapping
    community_user: CommunityUser
    user_attribute_value_mapping: AvmT[UserAttribute]

    _combined_cache: dict[AnyAttributeT, tuple[SlotStr, ...]] = field(
        init=False, default_factory=dict
    )

    @property
    def combined(self) -> MappingProxyType[AnyAttributeT, tuple[SlotStr, ...]]:
        if not self._combined_cache:
            self._combined_cache.update(self.attribute_value_mapping.combined.items())
            self._combined_cache.update(self.user_attribute_value_mapping.items())

        return MappingProxyType(self._combined_cache)
