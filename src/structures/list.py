from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import cached_property
import json
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Literal, Self, TypedDict

import mariadb

from database import queries
from discordtools import feedbackerrors as fbe
from utils import metautils, text

import pickle

from structures.user import User

from structures.attribute import AnyAttributeT, StaticAttribute, TaskAttribute, AttributeValueType, UserAttribute
from structures.task import Task

if TYPE_CHECKING:
    from structures.community import Community


class TaskAttributeResultT(TypedDict):
    id: int
    list_id: int
    name: str
    index: int
    value_type: int
    collection: bytes
    min_slots: int
    max_slots: int
    unique_slots: bool
    unique_value_per_list: bool

class TaskAttributeAliasResultT(TypedDict):
    task_attribute_id: int


class UserAttributeResultT(TypedDict):
    id: int
    list_id: int
    name: str
    index: int
    value_type: int
    collection: bytes
    min_slots: int
    max_slots: int
    unique_slots: bool

class UserAttributeAliasResultT(TypedDict):
    user_attribute_id: int


class TaskResultT(TypedDict):
    id: int
    name: str

class TaskAliasResultT(TypedDict):
    task_id: int


@dataclass(frozen=True, kw_only=True)
class List:
    MAX_NAME_LENGTH: ClassVar[int] = 64
    MAX_ATTRIBUTES: ClassVar[int] = 1
    MAX_TASKS: ClassVar[int] = 1

    INVALID_ENDING: ClassVar[str] = __name__.lower()

    community: 'Community'
    id: int
    name: str

    edit_lock: RLock = field(init=False, default_factory=RLock)

    @property
    def name_attribute(self) -> StaticAttribute[str]:
        return StaticAttribute(
            list=self,
            id=0,
            name='name',
            value_type=AttributeValueType.get_by_type(str),
            index=1,
            collection=[],
            min_slots=1,
            max_slots=1,
            unique_slots=False,
            get_value=lambda task: [task.name]
        )
    
    @property
    def alias_attribute(self) -> StaticAttribute[str]:
        return StaticAttribute(
            list=self,
            id=0,
            name='alias',
            value_type=AttributeValueType.get_by_type(str),
            index=2,
            collection=[],
            min_slots=0,
            max_slots=StaticAttribute.MAX_SLOTS,
            unique_slots=True,
            get_value=lambda task: sorted(task.aliases)
        )
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.community.identity

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    @classmethod
    def create(cls, community: 'Community', bad_name: str, *, cursor: mariadb.Cursor | None = None) -> 'List':
        from structures.community import Community

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

            with queries.connected(cursor) as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO list (
                        name
                    ) 
                    VALUES (
                        {h|name}
                    )
                """, h.steal())
                
                id: int = cursor.lastrowid  # type: ignore

                obj = cls(
                    community=community,
                    id=id,
                    name=name
                )

            return obj
            
            
    def delete(self) -> None:
        with self.edit_lock, self.community.edit_lock:
            # Check if list already deleted, but object used
            if self.community.get_list_by_id(self.id) is None:
                return
                
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM list
                    WHERE id = {h|self.id}
                """, h.steal())

        


    # --- All Attributes ---
    
    def get_attributes(self) -> list[AnyAttributeT]:
        return self.get_static_attributes() + self.get_task_attributes() + self.get_user_attributes()

    def get_attribute_by_name(self, name: str) -> AnyAttributeT | None:
        return (
            self.get_static_task_attribute_by_name(name)
            or self.get_task_attribute_by_name(name)
            or self.get_user_attribute_by_name(name)
        )
        
    def get_attribute_by_alias(self, alias: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_alias(alias)
            or self.get_task_attribute_by_alias(alias)
            or self.get_user_attribute_by_alias(alias)
        )

    def get_attribute_by_syn(self, syn: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_alias(syn)
            or self.get_task_attribute_by_syn(syn)
            or self.get_user_attribute_by_syn(syn)
        )
        

    # --- Static Attribute ---

    def _fetch_static_attribute(self, where: Callable[[StaticAttribute], bool]) -> StaticAttribute | None:
        for attr in self.get_static_attributes():
            if where(attr):
                return attr
        return None
    
    def get_static_attributes(self) -> list[StaticAttribute]:
        return [self.name_attribute, self.alias_attribute]
    
    def get_static_task_attribute_by_name(self, name: str) -> StaticAttribute | None:
        name = text.norm_syn(name)
        return self._fetch_static_attribute(lambda attr: name == text.norm_syn(attr.name))

    def get_static_attribute_by_alias(self, alias: str) -> StaticAttribute | None:
        alias = text.norm_syn(alias)
        return self._fetch_static_attribute(lambda attr: alias in attr.aliases)
    
    def get_static_attribute_by_syn(self, syn: str) -> StaticAttribute | None:
        syn = text.norm_syn(syn)
        return self._fetch_static_attribute(lambda attr: syn == text.norm_syn(attr.name) or syn in attr.aliases)
        

    # --- Task Attributes ---
        
    def _fetch_task_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[TaskAttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM task_attribute
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[TaskAttributeResultT] = cursor.fetchall()

        return result
    
    def _task_attribute_data_to_obj(self, data: TaskAttributeResultT) -> TaskAttribute:
        return TaskAttribute(
            list=self,
            id=data['id'],
            name=data['name'],
            index=data['index'],
            value_type=AttributeValueType.get_by_id(data['value_type']),
            collection=pickle.loads(data['collection']),
            min_slots=data['min_slots'],
            max_slots=data['max_slots'],
            unique_slots=data['unique_slots'],
            unique_value_per_list=data['unique_value_per_list']
        )
    
    def get_task_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[TaskAttribute]:
        return [
            self._task_attribute_data_to_obj(data) 
            for data in self._fetch_task_attributes_from_table(where)
        ]

    def get_task_attribute_by_id(self, id: int) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"id = {h|id}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_name(self, name: str) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"name = {h|name}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_alias(self, alias: str) -> TaskAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT task_attribute_id
                FROM task_attribute_alias
                WHERE
                    list_id = {h|self.id}
                    AND alias = {h|alias}
            """, h.steal())

            result: TaskAttributeAliasResultT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_attribute_by_id(result['task_attribute_id'])

    def get_task_attribute_by_syn(self, syn: str) -> TaskAttribute | None:
        return (
            self.get_task_attribute_by_name(syn)
            or self.get_task_attribute_by_alias(syn)
        )


    # --- User Attributes ---

    def _fetch_user_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[UserAttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM user_attribute
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[UserAttributeResultT] = cursor.fetchall()

        return result
    
    def _user_attribute_data_to_obj(self, data: UserAttributeResultT) -> UserAttribute:
        return UserAttribute(
            list=self,
            id=data['id'],
            name=data['name'],
            index=data['index'],
            value_type=AttributeValueType.get_by_id(data['value_type']),
            collection=pickle.loads(data['collection']),
            min_slots=data['min_slots'],
            max_slots=data['max_slots'],
            unique_slots=data['unique_slots']
        )
    
    def get_user_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[UserAttribute]:
        return [
            self._user_attribute_data_to_obj(data) 
            for data in self._fetch_user_attributes_from_table(where)
        ]

    def get_user_attribute_by_id(self, id: int) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"id = {h|id}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_name(self, name: str) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"name = {h|name}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_alias(self, alias: str) -> UserAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT user_attribute_id
                FROM user_attribute_alias
                WHERE
                    list_id = {h|self.id}
                    AND alias = {h|alias}
            """, h.steal())

            result: UserAttributeAliasResultT | None = cursor.fetchone()
        
        if result is None:
            return None
        
        return self.get_user_attribute_by_id(result['user_attribute_id'])

    def get_user_attribute_by_syn(self, syn: str) -> UserAttribute | None:
        return (
            self.get_user_attribute_by_name(syn)
            or self.get_user_attribute_by_alias(syn)
        )


    # --- Tasks ---

    def _fetch_tasks_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[TaskResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM task
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[TaskResultT] = cursor.fetchall()

        return result
    
    def _task_data_to_obj(self, data: TaskResultT) -> Task:
        return Task(
            list=self,
            id=data['id'],
            name=data['name']
        )
    
    def get_tasks(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Task]:
        return [
            self._task_data_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        ]

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"id = {h|id}")
        return self._task_data_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, name: str) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"name = {h|name}")
        return self._task_data_to_obj(data[0]) if data else None

    def get_task_by_alias(self, alias: str) -> Task | None:
        alias = text.sanitize(alias)
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT task_id
                FROM task_alias
                WHERE 
                    list_id = {h|self.id}
                    AND alias = {h|alias}
            """, h.steal())

            result: TaskAliasResultT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_by_id(result['task_id'])