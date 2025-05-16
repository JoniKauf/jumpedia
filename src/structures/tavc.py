from dataclasses import dataclass, field
import pickle
from typing import TYPE_CHECKING, TypedDict

from database import queries

from discordtools import feedbackerrors as fbe


if TYPE_CHECKING:
    from structures.attribute import AnyAttributeT, AttributeValueTypeT, StaticAttribute, TaskAttribute, UserAttribute
    from structures.task import Task

type TavcAttributeT = StaticAttribute | TaskAttribute
type TauvcAttributeT = TavcAttributeT | UserAttribute

@dataclass(frozen=True, kw_only=True)
class AbstractTavc[T: AnyAttributeT]:
    """Abstract Task Attribute Value Collection"""

    task: 'Task'
    mapping: dict[T, list['AttributeValueTypeT']] = field(init=False, default_factory=dict)

    @property
    def sorted_attributes(self) -> list[T]:
        return [
            attr for attr in sorted(
                self.mapping, key=lambda a: a.index
            )
        ]
    
    @property
    def sorted_values(self) -> list[list['AttributeValueTypeT']]:
        return [
            v for _, v in (
                sorted(self.mapping.items(), key=lambda item: item[0].index)
            )
        ]
    
    @property
    def sorted_items(self) -> list[tuple[T, list['AttributeValueTypeT']]]:
        return [
            (attr, v) for attr, v in (
                sorted(self.mapping.items(), key=lambda item: item[0].index)
            )
        ]
    
    @property
    def identity(self) -> tuple[int, ...]:
        return self.task.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    def __post_init__(self) -> None:
        if self.__class__ == AbstractTavc:
            raise NotImplementedError()
        
        self._add_static_attributes()
        self._add_task_attributes()
    
    def _add_static_attributes(self) -> None:
        for attr in self.task.list.get_static_attributes():
            self.mapping[attr] = attr.get_value(self.task)  # type: ignore
    
    def _add_task_attributes(self) -> None:
        h = queries.ArgHelper()

        with queries.connected(self.task.list.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM task_attribute_value
                WHERE task_id = {h|self.task.id}
            """, h.steal())

            result: list[TavcResultT] = cursor.fetchall()

        # Get all attributes specified for this task
        attributes = self.task.list.get_task_attributes(
            lambda h: f"id in ({','.join((h|(row['task_attribute_id'])) for row in result)})"
        )

        attribute_lookup: dict[int, TaskAttribute] = {
            attr.id: attr for attr in attributes
        }
        
        for row in result:
            try:
                attr = attribute_lookup.pop(row['task_attribute_id'])
            except KeyError:
                raise fbe.TemporaryFeedbackError("Data changed")
            
            val: list[AttributeValueTypeT] = pickle.loads(row['value'])
            
            self.mapping[attr] = val  # type: ignore

        if attribute_lookup:
            raise fbe.TemporaryFeedbackError("Data changed")


class TavcResultT(TypedDict):
    task_id: int
    task_attribute_id: int
    value: bytes

@dataclass(frozen=True, kw_only=True)
class Tavc(AbstractTavc[TavcAttributeT]):
    """Task Attribute Value Collection"""


class TuavcResultT(TypedDict):
    task_id: int
    user_id: int
    user_attribute_id: int
    value: bytes

@dataclass(frozen=True, kw_only=True)
class Tuavc(AbstractTavc[TauvcAttributeT]):
    """Task User Attribute Value Collection"""

    user_id: int

    def __post_init__(self) -> None:
        super().__post_init__()
        self._add_user_attributes()

    def _add_user_attributes(self) -> None:
        h = queries.ArgHelper()

        with queries.connected(self.task.list.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM task_user_attribute_value
                WHERE 
                    task_id = {h|self.task.id}
                    AND user_id = {h|self.user_id}
            """, h.steal())

            result: list[TuavcResultT] = cursor.fetchall()

        # Get all attributes specified for this task
        attributes = self.task.list.get_user_attributes(
            lambda h: f"id in ({','.join((h|(row['user_attribute_id'])) for row in result)})"
        )

        attribute_lookup: dict[int, UserAttribute] = {
            attr.id: attr for attr in attributes
        }

        for row in result:
            try:
                attr = attribute_lookup.pop(row['user_attribute_id'])
            except KeyError:
                raise fbe.TemporaryFeedbackError("Data changed")
            
            val: list[AttributeValueTypeT] = pickle.loads(row['value'])
            
            self.mapping[attr] = val 

        if attribute_lookup:
            raise fbe.TemporaryFeedbackError("Data changed")
        