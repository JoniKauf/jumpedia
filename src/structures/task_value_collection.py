from dataclasses import dataclass, field
from typing import Any, Never

from structures.attribute import AnyAttributeT, AttributeValueTypeT, StaticAttribute, TaskAttribute
from structures.task import Task




@dataclass(frozen=True, kw_only=True)
class AbstractTaskValueCollectin:
    task: Task
    data: dict[Any, list[AttributeValueTypeT]]

    @property
    def identity(self) -> tuple[int, ...]:
        return self.task.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    def __post_init__(self) -> None:
        if self.__class__ == AbstractTaskValueCollectin:
            raise NotImplementedError()
    
    @classmethod
    def create(cls, *args: Any, **kwargs: Any) -> Never:
        raise NotImplementedError()
    

@dataclass(frozen=True, kw_only=True)
class TaskValueCollection:
    data: dict[StaticAttribute | TaskAttribute, list[AttributeValueTypeT]]


@dataclass(frozen=True, kw_only=True)
class UserTaskValueCollection:
    data: dict[AnyAttributeT, list[AttributeValueTypeT]]