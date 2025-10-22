import typing as t
from dataclasses import dataclass, field
from types import MappingProxyType

from structures.attribute import (
    AnyAttributeT,
    StaticAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.attribute.slot_type import SlotStr
from structures.user.community_user import CommunityUser

if t.TYPE_CHECKING:
    from structures.task import Task

type AvmT[T: AnyAttributeT] = MappingProxyType[T, tuple[SlotStr, ...]]


@dataclass(frozen=True, slots=True)
class AttributeValueMapping:
    task: Task
    static_attribute_value_mapping: AvmT[StaticAttribute]
    task_attribute_value_mapping: AvmT[TaskAttribute]
    user_attribute_value_mapping: tuple[CommunityUser, AvmT[UserAttribute]] | None

    _combined_cache: dict[AnyAttributeT, tuple[SlotStr, ...]] = field(
        init=False, default_factory=dict
    )
    python_id: int = field(init=False, default=-1)

    def __post_init__(self):
        object.__setattr__(self, "python_id", id(self))

    @property
    def combined(self) -> MappingProxyType[AnyAttributeT, tuple[SlotStr, ...]]:
        if not self._combined_cache:
            self._combined_cache.update(self.static_attribute_value_mapping.items())
            self._combined_cache.update(self.task_attribute_value_mapping.items())

            if self.user_attribute_value_mapping is not None:
                self._combined_cache.update(
                    self.user_attribute_value_mapping[1].items()
                )

        return MappingProxyType(self._combined_cache)
