import ast
from dataclasses import astuple, dataclass, field
import sys
from threading import RLock
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Iterable, Literal, Optional, Self, Sequence, TypeAlias, TypedDict, cast, get_args, TYPE_CHECKING
from database import queries
from discordtools import feedbackerrors as fbe
from structures.attribute import Attribute, AttributeTableT
from structures.community import Community
from structures.task import Task
from utils import text

class ListTableT(TypedDict):
    id: int
    name: str
    display_name: str
    community_id: int

@dataclass(frozen=True, kw_only=False)
class List:
    id: int
    name: str
    display_name: str
    community: Community

    attributes: set[Attribute] = field(init=False, default_factory=set)
    attribute_id_mapping: dict[int, Attribute] = field(init=False, default_factory=dict)
    attribute_name_mapping: dict[str, Attribute] = field(init=False, default_factory=dict)

    edit_lock: RLock = field(init=False, default_factory=RLock)

    TABLE_NAME: ClassVar[str] = "list"
    MAX_NAME_LENGTH: ClassVar[int] = 50

    def __post_init__(self) -> None:
        self.reload_attributes()

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, List) and self.id == value.id

    def _add_to_attribute_collection(self, attribute: Attribute):
        with self.edit_lock:
            self.attributes.add(attribute)
            self.attribute_id_mapping[attribute.id] = attribute
            self.attribute_name_mapping[attribute.name] = attribute
    
    def reload_attributes(self) -> None:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [Attribute.TABLE_NAME])

            result: list[AttributeTableT] = cursor.fetchall()

        with self.edit_lock:
            self.attributes.clear()

            for a_data in result:
                self.attributes.add(Attribute(
                    a_data['id'],
                    a_data['name'],
                    a_data['display_name'],
                    set(a_data['alias']),
                    a_data['value_type'], #
                    a_data['value_collection'],
                    a_data['min_value_slots'],
                    a_data['max_value_slots'],
                    a_data['unique_slots'],
                    a_data['user_bound'],
                    a_data['list_behaviour'],
                    self
                ))

            self.task_id_mapping.clear()
            self.task_name_mapping.clear()

            for list_ in self.lists:
                self.task_id_mapping[list_.id] = list_
                self.task_name_mapping[list_.name] = list_

    def create_attribute(self, default_value):
        with self.edit_lock:
            
            

    @classmethod
    def filter(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        lst = List._get_builtin_list(list_)

        ...

    @classmethod
    def sort(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        lst = List._get_builtin_list(list_)

        expression = text.fix_whitespace(expression, " ", True)

        parts = expression.split(" ")

        ...

