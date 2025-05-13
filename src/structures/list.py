from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
import json
from threading import RLock
from typing import Any, Callable, ClassVar, Final, Iterable, Literal, Self, TypedDict

import mariadb
from database import queries
from discordtools import feedbackerrors as fbe
from structures.attribute import AnyAttribute, Attribute, AbstractAttribute, AttributeAliasResultT, AttributeResultT, AttributeValueType, UserAttribute, UserAttributeAliasResultT, UserAttributeResultT
from structures.community import Community
from structures.task import AbstractTask, Task, TaskResultT

import pickle

from structures.user import User
from utils import metautils, text

class ListResultT(TypedDict):
    id: int
    name: str
    community_id: int

@dataclass(frozen=True, kw_only=True)
class List:
    MAX_NAME_LENGTH: ClassVar[Final[int]] = 64
    MAX_ATTRIBUTES: ClassVar[Final[int]] = 1
    MAX_TASKS: ClassVar[Final[int]] = 1

    INVALID_ENDING: ClassVar[Final[str]] = __name__.lower()

    community: Community
    id: int
    name: str

    edit_lock: RLock = field(init=False, default_factory=RLock)

    @cached_property
    def special_name_attribute(self) -> Attribute[str]:
        return Attribute.create(
            list=self,
            bad_name='name',
            bad_aliases=(),
            value_type=AttributeValueType.get_by_type(str),
            str_user_collection=None,
            min_slots=1,
            max_slots=1,
            unique_slots=False,
            unique_value_per_list=True,
            special=True
        )
    
    @cached_property
    def special_alias_attribute(self) -> Attribute[str]:
        return Attribute.create(
            list=self,
            bad_name='alias',
            bad_aliases=(),
            value_type=AttributeValueType.get_by_type(str),
            str_user_collection=None,
            min_slots=0,
            max_slots=Attribute.MAX_SLOTS,
            unique_slots=True,
            unique_value_per_list=True,
            special=True
        )

    @property
    def special_attributes(self) -> list[Attribute[str]]:
        return [self.special_name_attribute, self.special_alias_attribute]
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.community.identity
    
    def __post_init__(self) -> None:
        self.get_attributes()

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    @classmethod
    def create(cls, community: Community, bad_name: str) -> 'List':
        with community.edit_lock:
            lists = community.get_lists()

            name = text.validate_and_sanitize_name(
                bad_name, 
                cls.MAX_NAME_LENGTH, 
                (list.name for list in lists)
            )

            if name.endswith(cls.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out `{cls.INVALID_ENDING}` from the name, as it is redundant!")
            
            if len(lists) >= Community.MAX_LISTS:
                raise fbe.TemporaryFeedbackError("Limit reached")
            
            h = queries.ArgHelper()

            with queries.connected(community) as (conn, cursor):
                try:
                    cursor.execute(f"""
                        INSERT INTO list
                        (name)
                        VALUES ({h|name})
                    """, h.steal())
                except mariadb.IntegrityError:
                    raise fbe.TemporaryFeedbackError(f"List with that name exists already")
                
                obj = List(
                    community=community,
                    id=cursor.lastrowid,  # type: ignore
                    name=name
                )

            _ = obj.special_attributes
            return obj

    # --- Attributes ---

    def _fetch_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[AttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT
                    a.*,
                    COALESCE(JSON_ARRAYAGG(aa.alias), JSON_ARRAY()) AS aliases
                FROM attribute a
                LEFT JOIN attribute_alias aa ON aa.attribute_id = a.id
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
                GROUP BY a.id
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
            aliases=json.loads(data['aliases']),
            index=data['index'],
            value_type=AttributeValueType.get_by_id(data['value_type']),
            collection=pickle.loads(data['collection']),
            min_slots=data['min_slots'],
            max_slots=data['max_slots'],
            unique_slots=data['unique_slots'],
            unique_value_per_list=data['unique_value_per_list'],
            special=data['special']
        )
    
    def get_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Attribute]:
        return [self.special_name_attribute, self.special_alias_attribute] + [self._attribute_data_to_obj(data) for data in self._fetch_attributes_from_table(where)]

    def get_attribute_by_id(self, id: int) -> Attribute:
        data = self._fetch_attributes_from_table(lambda h: f"id = {h|id}")
        return self._attribute_data_to_obj(data[0] if data else None)
    
    def get_attribute_by_name(self, name: str) -> Attribute:
        name = text.sanitize(name)
        data = self._fetch_attributes_from_table(lambda h: f"name = {h|name}")
        return self._attribute_data_to_obj(data[0] if data else None)
    
    def get_attribute_by_alias(self, alias: str) -> Attribute:
        alias = text.sanitize(alias)
        h = queries.ArgHelper()

        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT 
                    attribute_id
                FROM 
                    attribute_alias
                WHERE 
                    alias = {h|alias}
            """, h.steal())

            result: AttributeAliasResultT | None = cursor.fetchone()

        if result is None:
            raise fbe.TemporaryFeedbackError("Attribute with that alias doesn't exist")
        
        return self.get_attribute_by_id(result['attribute_id'])

    def get_attribute_by_syn(self, syn: str) -> Attribute:
        try:
            return self.get_attribute_by_name(syn)
        except fbe.TemporaryFeedbackError:  # TODO NotAnAttributeError
            return self.get_attribute_by_alias(syn)


    # --- User Attributes ---

    def _fetch_user_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[UserAttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT
                    ua.*,
                    COALESCE(JSON_ARRAYAGG(uaa.alias), JSON_ARRAY()) AS aliases
                FROM user_attribute ua
                LEFT JOIN user_attribute_alias uaa ON uaa.user_attribute_id = ua.id
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
                GROUP BY ua.id
            """, h.steal())

            result: list[UserAttributeResultT] = cursor.fetchall()

        return result
    
    def _user_attribute_data_to_obj(self, data: UserAttributeResultT | None) -> UserAttribute:
        if data is None:
            raise fbe.TemporaryFeedbackError("Attribute does not exist!")

        return UserAttribute(
            list=self,
            id=data['id'],
            name=data['name'],
            aliases=json.loads(data['aliases']),
            index=data['index'],
            value_type=AttributeValueType.get_by_id(data['value_type']),
            collection=pickle.loads(data['collection']),
            min_slots=data['min_slots'],
            max_slots=data['max_slots'],
            unique_slots=data['unique_slots']
        )
    
    def get_user_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[UserAttribute]:
        return [self._user_attribute_data_to_obj(data) for data in self._fetch_user_attributes_from_table(where)]

    def get_user_attribute_by_id(self, id: int) -> UserAttribute:
        data = self._fetch_user_attributes_from_table(lambda h: f"id = {h|id}")
        return self._user_attribute_data_to_obj(data[0] if data else None)
    
    def get_user_attribute_by_name(self, name: str) -> UserAttribute:
        name = text.sanitize(name)
        data = self._fetch_user_attributes_from_table(lambda h: f"name = {h|name}")
        return self._user_attribute_data_to_obj(data[0] if data else None)
    
    def get_user_attribute_by_alias(self, alias: str) -> UserAttribute:
        alias = text.sanitize(alias)
        h = queries.ArgHelper()

        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT 
                    user_attribute_id
                FROM 
                    user_attribute_alias
                WHERE 
                    alias = {h|alias}
            """, h.steal())

            result: UserAttributeAliasResultT | None = cursor.fetchone()

        if result is None:
            raise fbe.TemporaryFeedbackError("Attribute with that alias doesn't exist")
        
        return self.get_user_attribute_by_id(result['user_attribute_id'])

    def get_user_attribute_by_syn(self, syn: str) -> UserAttribute:
        try:
            return self.get_user_attribute_by_name(syn)
        except fbe.TemporaryFeedbackError:  # TODO NotAnAttributeError
            return self.get_user_attribute_by_alias(syn)

    # --- All Attributes ---
    
    def get_all_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[AnyAttribute]:
        return self.get_attributes(where) + self.get_user_attributes(where)

    def get_any_attribute_by_id(self, id: int) -> AnyAttribute:
        try:
            return self.get_attribute_by_id(id)
        except fbe.TemporaryFeedbackError:  # TODO except AttributeDoesNotExist
            return self.get_user_attribute_by_id(id)
    
    def get_any_attribute_by_name(self, name: str) -> AnyAttribute:
        try:
            return self.get_attribute_by_name(name)
        except fbe.TemporaryFeedbackError:  # TODO except AttributeDoesNotExist
            return self.get_user_attribute_by_name(name)
        
    def get_any_attribute_by_alias(self, alias: str) -> AnyAttribute:
        try:
            return self.get_attribute_by_alias(alias)
        except fbe.TemporaryFeedbackError:  # TODO except AttributeDoesNotExist
            return self.get_user_attribute_by_alias(alias)
        
    def get_any_attribute_by_syn(self, syn: str) -> AnyAttribute:
        try:
            return self.get_attribute_by_syn(syn)
        except fbe.TemporaryFeedbackError:  # TODO except AttributeDoesNotExist
            return self.get_user_attribute_by_syn(syn)


    # --- Tasks ---

    def _fetch_tasks_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[TaskResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT 
                    id
                FROM 
                    task
                WHERE
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[TaskResultT] = cursor.fetchall()

        return result
    
    def _task_data_to_obj(self, data: TaskResultT | None) -> Task:
        if data is None:
            raise fbe.TemporaryFeedbackError("Task does not exist!")

        return Task(
            list=self,
            id=data['id']
        )
    
    def get_tasks(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Task]:
        return [self._task_data_to_obj(data) for data in self._fetch_tasks_from_table(where)]

    def get_task_by_id(self, id: int) -> Task:
        data = self._fetch_tasks_from_table(lambda h: f"id = {h|id}")
        return self._task_data_to_obj(data[0] if data else None)
    
    def get_task_by_name(self, name: str) -> Task:
        data = self._fetch_tasks_from_table(lambda h: f"")


    def update_task_names(self)
    
    @classmethod
    def filter(cls, list_: list[AbstractTask] | Self, expression: str) -> list[AbstractTask]:
        ...

    @classmethod
    def sort(cls, list_: list[AbstractTask] | Self, expression: str) -> list[AbstractTask]:
        ...

        expression = text.fix_whitespace(expression, " ", True)

        parts = expression.split(" ")

        return []

