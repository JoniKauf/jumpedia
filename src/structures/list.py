from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Final, Iterable, Self, TypedDict

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
    MAX_NAME_LENGTH: ClassVar[Final[int]] = 64
    INVALID_ENDING: ClassVar[Final[str]] = __name__.lower()
    MAX_LISTS_PER_COMMUNITY: ClassVar[Final[int]] = 1

    community: Community
    id: int
    name: str
    display_name: str
    
    _id_attribute: Attribute[int] | None = field(init=False, default=None)
    _key_attribute: Attribute[str] | None = field(init=False, default=None)

    @property
    def id_attribute(self) -> Attribute[int]:
        if self._id_attribute is None:
            raise fbe.TemporaryFeedbackError()
        return self._id_attribute
    
    @property
    def key_attribute(self) -> Attribute[str]:
        if self._key_attribute is None:
            raise fbe.TemporaryFeedbackError()
        return self._key_attribute

    @property
    def attribute_table_name(self) -> str:
        return f"{Attribute.TABLE_PREFIX}{self.id}"
    
    @property
    def task_table_name(self) -> str:
        return f"{Task.TABLE_PREFIX}{self.id}"
    
    @property
    def user_task_table_name(self) -> str:
        return f"{Task.USER_TABLE_PREFIX}{self.id}"
    
    def __post_init__(self) -> None:
        self.get_attributes()

    def __hash__(self) -> int:
        return hash((self.id, hash(self.community)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, List) and self.id == value.id and self.community == value.community
    
    @classmethod
    def create(cls, community: Community, bad_name: str, key_attribute_name: str, key_attribute_alias: Iterable[str]) -> 'List':
        with community.edit_lock:
            lists = community.get_lists()

            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True, 
                Community.MAX_NAME_LENGTH,
                (list.name for list in lists)
            )

            if name.endswith(cls.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out `{cls.INVALID_ENDING}` from the name, as it is redundant!")
            
            if len(lists) >= List.MAX_LISTS_PER_COMMUNITY:
                raise fbe.TemporaryFeedbackError("Limit reached")
            
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

                # Like in community, if anything goes wrong in here, the rest
                # from before will also be reset
                obj._init_tables(key_attribute_name, key_attribute_alias)

            return obj
    
    def _init_tables(self, key_attribute_name: str, key_attribute_alias: Iterable[str]) -> None:
        with self.community.edit_lock:
            with queries.connected(self.community) as (conn, cursor):
                cursor.execute(f"""
                    CREATE TABLE `{self.attribute_table_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        list_id INT NOT NULL,
                        name VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL,
                        display_name VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL,
                        sort_value INT NOT NULL UNIQUE,
                        alias JSON NOT NULL,
                        value_type INT NOT NULL,
                        collection BLOB NOT NULL,
                        min_value_slots INT NOT NULL,
                        max_value_slots INT NOT NULL,
                        unique_slots BOOL NOT NULL,
                        user_bound BOOL NOT NULL,
                        unique_value_per_list BOOL NOT NULL,
                        predefined BOOL NOT NULL,

                        FOREIGN KEY (list_id)
                            REFERENCES list(id)
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE `{self.task_table_name}`
                """)

    def _generate_default_attributes(self, key_attribute_name: str, key_attribute_alias: Iterable[str]) -> None:
        Attribute.create(
            list=self,
            bad_name='id',
            bad_aliases=(),
            sort_value=0,
            value_type=AttributeValueType.get_by_type(int),
            str_user_collection=None,
            min_value_slots=1,
            max_value_slots=1,
            unique_slots=True,
            user_bound=False,
            unique_value_per_list=True,
            predefined=False
        )

        Attribute.create(
            list=self,
            bad_name=key_attribute_name,
            bad_aliases=key_attribute_alias,
            sort_value=Attribute.SORT_KEY_LAST_NUMBER
        )

    def _fetch_atttributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[AttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {h|self.attribute_table_name}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[AttributeResultT] = cursor.fetchall()

        return result
    
    def _attribute_data_to_obj[T](self, data: AttributeResultT | None) -> Attribute:
        if data is None:
            raise fbe.TemporaryFeedbackError("Attribute does not exist!")

        return Attribute(
            list=self,
            id=data['id'],
            name=data['name'],
            display_name=data['display_name'],
            sort_value=data['sort_value'],
            alias=set(data['alias']),
            value_type=AttributeValueType.get_by_id(data['value_type']),
            collection=pickle.loads(data['collection']),
            min_value_slots=data['min_value_slots'],
            max_value_slots=data['max_value_slots'],
            unique_slots=data['unique_slots'],
            user_bound=data['user_bound'],
            unique_value_per_list=data['unique_value_per_list'],
            predefined=data['predefined']
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

