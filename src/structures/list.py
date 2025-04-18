import ast
from dataclasses import astuple, dataclass, field
import json
import sys
from threading import RLock
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Self, Sequence, TypeAlias, TypedDict, cast, get_args, TYPE_CHECKING
from database import queries
from discordtools import feedbackerrors as fbe
from structures import attribute
from structures.attribute import Attribute
from structures import attribute as attr
from structures.community import Community
from structures.task import Task
from utils import jsonutils, text

import pickle


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

    edit_lock: RLock = field(init=False, default_factory=RLock)

    TABLE_NAME: ClassVar[str] = "list"
    MAX_NAME_LENGTH: ClassVar[int] = 50

    def __post_init__(self) -> None:
        self.get_attributes()

    def __hash__(self) -> int:
        return hash(self.id)

    def create_attribute[T: attr.AttributeValueTypeT](
        self,
        bad_name: str,
        bad_aliases: set[str],
        sort_value: int,
        value_type: attr.AttributeValueType[T],
        user_value_collection: str | None,
        min_value_slots: int,
        max_value_slots: int,
        unique_slots: bool,
        user_bound: bool,
        unique_in_list: bool,
    ):
        with self.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True, 
                Attribute.MAX_SYN_LEN, 
                (a.name for a in self.get_attributes())
            )

            alias = text.fix_aliases(bad_aliases, Attribute.MAX_SYN_LEN, Attribute.MAX_ALIASES)
            
            Attribute._check_generic_number_valid(sort_value)
            
            if not (1 <= max_value_slots <= Attribute.MAX_VALUE_SLOTS):
                raise fbe.TemporaryFeedbackError()

            if not (0 <= min_value_slots <= max_value_slots):
                raise fbe.TemporaryFeedbackError()
            
            with queries.connected(self.community) as (conn, cursor):
                cursor.execute("""

                """)
                
            obj = Attribute(
                self,
                id,
                name,
                display_name,
                sort_value,
                alias,
                value_type,
                List.parse_user_collection(
                    jsonutils.json_loads_safe(user_value_collection, Attribute.MAX_DEPTH),
                    value_type,
                ),
                min_value_slots,
                max_value_slots,
                unique_slots,
                user_bound,
                unique_in_list
            ) 

            return obj

    @classmethod
    def parse_user_collection[T: attr.AttributeValueTypeT](
        cls, 
        user_value_collection: attr.UserCollectionT, 
        value_type: attr.AttributeValueType[T]
    ) -> attr.CollectionT:
        if user_value_collection is None:
            return None
        
        if not isinstance(user_value_collection, list):
            raise fbe.TemporaryFeedbackError("Not a tree")
        
        return cls.parse_user_collection_tree(user_value_collection, value_type)

    
    @classmethod
    def parse_user_collection_tree[T: attr.AttributeValueTypeT](
        cls, 
        user_collection_tree: attr.UserCollectionTreeT, 
        value_type: attr.AttributeValueType[T]
    ) -> attr.CollectionTreeT[T]:
        result: attr.CollectionTreeT = []

        for item in user_collection_tree:
            value, display_value, sort_value = cls.extract_generic_data_from_collection_item(item, value_type)

            sub_trees = item.get('children', [])

            if not isinstance(sub_trees, list):
                raise fbe.TemporaryFeedbackError("Not a sub tree")
            
            result.append(attr.CollectionTreeItem(
                value,
                display_value,
                sort_value,
                List.parse_user_collection_tree([sub_tree for sub_tree in sub_trees], value_type) 
            ))

        return result
    
    @classmethod
    def extract_generic_data_from_collection_item[T: attr.AttributeValueTypeT](
        cls, 
        item: attr.UserCollectionTreeItemT,
        value_type: attr.AttributeValueType[T]
    ) -> tuple[T, T, int]:
        try:
            sort_value: int = int(item['sort_value'])
        except KeyError as e:
            raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
        except ValueError as e:
            raise fbe.TemporaryFeedbackError("Not an int")
            
        Attribute._check_generic_number_valid(sort_value)

        try:
            bad_value = item['value']
        except KeyError as e:
            raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
        
        display_value: T = Attribute._parse_str_singular(bad_value, value_type)
        value: T = Attribute.normalize(display_value)

        return (value, display_value, sort_value)
    
    def get_attributes(self) -> list[Attribute]:
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [Attribute.TABLE_NAME])

            result: list[attr.AttributeTableT] = cursor.fetchall()
        
        attributes: list[Attribute] = []

        for a_data in result:
            attributes.append(Attribute(
                self,
                a_data['id'],
                a_data['name'],
                a_data['display_name'],
                a_data['sort_value'],
                set(a_data['alias']),
                attr.AttributeValueType.lookup_by_id(a_data['value_type']),
                pickle.loads(a_data['value_collection']),
                a_data['min_value_slots'],
                a_data['max_value_slots'],
                a_data['unique_slots'],
                a_data['user_bound'],
                a_data['unique_in_list']
            ))

        return attributes
    
    
        
        


    @classmethod
    def filter(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        ...

    @classmethod
    def sort(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        ...

        expression = text.fix_whitespace(expression, " ", True)

        parts = expression.split(" ")

        return []

