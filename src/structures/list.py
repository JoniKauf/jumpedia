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

import pickle

from utils import text


class ListTableT(TypedDict):
    id: int
    name: str
    display_name: str
    community_id: int

@dataclass(frozen=True, kw_only=True)
class List:
    community: Community
    id: int
    name: str
    display_name: str

    edit_lock: RLock = field(init=False, default_factory=RLock)

    TABLE_NAME: ClassVar[str] = "list"
    MAX_NAME_LENGTH: ClassVar[int] = 50

    def __post_init__(self) -> None:
        self.get_attributes()

    def __hash__(self) -> int:
        return hash((self.id, hash(self.community)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, List) and self.id == value.id and self.community == value.community
    
    @classmethod
    def create(cls, community: Community, bad_name: str) -> 'List':
        with community.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True, 
                Community.MAX_NAME_LENGTH,
                (list.name for list in community.get_lists())
            )
            
            INVALID_ENDING = List.__name__.lower()

            if name.endswith(INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out `{INVALID_ENDING}` from the name, as it is redundant!")
            
            h = queries.ArgHelper()

            with queries.connected(community) as (conn, cursor):
                cursor.execute(f"""
                    SELECT *
                    FROM {h|List.TABLE_NAME}
                    WHERE name = {h|name}
                """, h.steal())

                result_opt: ListTableT | None = cursor.fetchone()

                if result_opt:
                    raise fbe.TemporaryFeedbackError(f"{List.TABLE_NAME.title()} with that name exists already")
                
                cursor.execute(f"""
                    INSERT INTO {h|List.TABLE_NAME}
                    (name, display_name)
                    VALUES ({h|name}, {h|display_name})
                """, h.steal())
            
            obj = List(
                community,
                cursor.lastrowid,  # type: ignore
                name,
                display_name
            ) 

            return obj
        
    def get_attributes(self) -> list[Attribute]:
        h = queries.ArgHelper()

        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT * 
                FROM {h|Attribute.TABLE_NAME}
            """, h.steal())

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
                pickle.loads(a_data['collection']),
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

