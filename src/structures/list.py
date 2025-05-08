from dataclasses import dataclass
from typing import Callable, ClassVar, Self, TypedDict

import mariadb
from database import queries
from discordtools import feedbackerrors as fbe
from structures.attribute import Attribute, AttributeResultT, AttributeValueType
from structures.community import Community
from structures.task import Task

import pickle

from utils import text

class ListResultT(TypedDict):
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

    MAX_NAME_LENGTH: ClassVar[int] = 50

    def __post_init__(self) -> None:
        self.get_attributes()

    def __hash__(self) -> int:
        return hash((self.id, hash(self.community)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, List) and self.id == value.id and self.community == value.community
    
    @classmethod
    def create(cls, community: Community, bad_name: str) -> 'List':
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
            try:
                cursor.execute(f"""
                    INSERT INTO list
                    (name, display_name)
                    VALUES ({h|name}, {h|display_name})
                """, h.steal())
            except mariadb.IntegrityError:
                raise fbe.TemporaryFeedbackError(f"List with that name exists already")
            
        obj = List(
            community=community,
            id=cursor.lastrowid,  # type: ignore
            name=name,
            display_name=display_name
        ) 

        return obj
    
    def _fetch_atttributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[AttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {h|Attribute.TABLE_NAME}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[AttributeResultT] = cursor.fetchall()

        return result
    
    def _attribute_data_to_obj(self, data: AttributeResultT | None) -> Attribute:
        if data is None:
            raise fbe.TemporaryFeedbackError("Attribute does not exist!")

        return Attribute(
            list=self,
            id=data['id'],
            name=data['name'],
            display_name=data['display_name'],
            sort_value=data['sort_value'],
            alias=set(data['alias']),
            value_type=AttributeValueType.lookup_by_id(data['value_type']),
            collection=pickle.loads(data['collection']),
            min_value_slots=data['min_value_slots'],
            max_value_slots=data['max_value_slots'],
            unique_slots=data['unique_slots'],
            user_bound=data['user_bound'],
            unique_in_list=data['unique_in_list']
        )
    
    def get_attributes(self) -> list[Attribute]:
        return [self._attribute_data_to_obj(data) for data in self._fetch_atttributes_from_table(None)]

    def get_attribute_by_id(self, id: int) -> Attribute:
        data = self._fetch_atttributes_from_table(lambda h: f"id = {h|id}")
        return self._attribute_data_to_obj(data[0] if data else None)
    
    def get_attribute_by_name(self, name: str) -> Attribute:
        name = text.norm(name)
        data = self._fetch_atttributes_from_table(lambda h: f"id = {h|name}")
        return self._attribute_data_to_obj(data[0] if data else None)
    
    @classmethod
    def filter(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        ...

    @classmethod
    def sort(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        ...

        expression = text.fix_whitespace(expression, " ", True)

        parts = expression.split(" ")

        return []

