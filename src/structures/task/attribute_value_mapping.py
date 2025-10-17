
from dataclasses import dataclass, field
from types import MappingProxyType
from structures.attribute.static_attribute import StaticAttribute

from structures.attribute import AnyAttributeT
from structures.attribute.slot_type import TypeStr
from structures.attribute.task_attribute import TaskAttribute
from structures.attribute.user_attribute import UserAttribute
import typing as t

from structures.user.community_user import CommunityUser

if t.TYPE_CHECKING:
    from structures.task import Task

@dataclass(frozen=True, slots=True)
class AttributeValueMapping:
    task: Task
    static_attribute_value_mapping: MappingProxyType[StaticAttribute, list[TypeStr]]
    task_attribute_value_mapping: MappingProxyType[TaskAttribute, list[TypeStr]]
    user_attribute_value_mapping: tuple[CommunityUser, MappingProxyType[UserAttribute, list[TypeStr]]] | None

    _combined_cache: dict[AnyAttributeT, list[TypeStr]] = field(init=False, default_factory=dict)
    python_id: int = field(init=False)

    @property
    def combined(self) -> MappingProxyType[AnyAttributeT, list[TypeStr]]:
        if not self._combined_cache:
            self._combined_cache.update(
                self.static_attribute_value_mapping.items()
            )
            self._combined_cache.update(
                self.task_attribute_value_mapping.items()
            )
            
            if self.user_attribute_value_mapping is not None:
                self._combined_cache.update(
                    self.user_attribute_value_mapping[1].items()
                )
        
        return MappingProxyType(self._combined_cache)