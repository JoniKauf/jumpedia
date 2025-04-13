import ast
from dataclasses import astuple, dataclass, field
import sys
from threading import RLock
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Iterable, Literal, Optional, Self, Sequence, TypeAlias, TypedDict, cast, get_args, TYPE_CHECKING
from database import queries
from discordtools import feedbackerrors as fbe
from structures.attribute import Attribute
from structures import attribute as attr
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

            result: list[attr.AttributeTableT] = cursor.fetchall()

        with self.edit_lock:
            self.attributes.clear()
            self.attribute_id_mapping.clear()
            self.attribute_name_mapping.clear()

            for a_data in result:
                self._add_to_attribute_collection(Attribute(
                    a_data['id'],
                    self,
                    a_data['name'],
                    a_data['display_name'],
                    set(a_data['alias']),
                    attr.AttributeValueType.lookup_by_id(a_data['value_type']),
                    a_data['value_collection'],
                    a_data['min_value_slots'],
                    a_data['max_value_slots'],
                    a_data['unique_slots'],
                    a_data['user_bound'],
                    a_data['unique_in_list']
                ))

    def create_attribute[T: attr.AttributeValueTypeT](
        self,
        bad_name: str,
        alias: set[str],
        value_type: attr.AttributeValueType[T],
        value_collection: str,
        min_value_slots: int,
        max_value_slots: int,
        unique_slots: bool,
        user_bound: bool,
        unique_in_list: bool,
    ):
        with self.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, True, self.attribute_name_mapping
            )

    
    @classmethod
    def parse_user_tree[T](cls, tree: attr.CollectionTreeByUserT, value_type: attr.AttributeValueType) -> attr.CollectionTree[T]:
        try:
            sort_value_str = str(tree['sort_value'])
        except KeyError as e:
            raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
        
        # Parse int to check if it valid and in bounce...
        sort_value: int = Attribute._parse_str_singular(str(sort_value_str), attr.AttributeValueType.lookup_by_type(int))

        try:
            bad_value = tree['value']
        except KeyError as e:
            raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
        
        display_value: T = Attribute._parse_str_singular(bad_value, value_type)
        value: T = Attribute.normalize(display_value)

        sub_trees = tree.get('children', [])

        if not isinstance(sub_trees, list):
            raise fbe.TemporaryFeedbackError("Not a sub tree")
        
        return {
            'value': value,
            'display_value': display_value,
            'sort_value': sort_value,
            'children': [
                List.parse_user_tree(sub_tree, value_type) for sub_tree in sub_trees
            ]
        }


            

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

