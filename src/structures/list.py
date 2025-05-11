from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
import json
from typing import Any, Callable, ClassVar, Final, Iterable, Literal, Self, TypedDict

import mariadb
from database import queries
from discordtools import feedbackerrors as fbe
from structures.attribute import Attribute, AttributeResultT, AttributeValueType
from structures.community import Community
from structures.task import Task, TaskResultT

import pickle

from structures.user import User
from utils import metautils, text

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

    @cached_property
    def name_attribute(self) -> Attribute[str]:
        return Attribute.create(
            list=self,
            bad_name='name',
            bad_aliases=(),
            sort_value=1,
            value_type=AttributeValueType.get_by_type(str),
            str_user_collection=None,
            min_value_slots=1,
            max_value_slots=1,
            unique_slots=False,
            user_bound=False,
            unique_value_per_list=True,
            predefined=True
        )

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

            return obj
    
    def _fetch_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[AttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT 
                    a.*, 
                    JSON_ARRAYAGG(JSON_QUOTE(al.alias)) AS alias
                FROM attribute a
                LEFT JOIN attribute_alias aa ON aa.attribute_id = a.id
                LEFT JOIN alias al ON al.id = aa.alias_id
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
                GROUP BY a.id 
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
            alias=set(json.loads(data['alias'])),
            value_type=AttributeValueType.get_by_id(data['value_type']),
            collection=pickle.loads(data['collection']),
            min_value_slots=data['min_value_slots'],
            max_value_slots=data['max_value_slots'],
            unique_slots=data['unique_slots'],
            user_bound=data['user_bound'],
            unique_value_per_list=data['unique_value_per_list'],
            predefined=data['predefined']
        )
    
    def get_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Attribute]:
        return [self._attribute_data_to_obj(data) for data in self._fetch_attributes_from_table(where)]

    def get_attribute_by_id(self, id: int) -> Attribute:
        data = self._fetch_attributes_from_table(lambda h: f"id = {h|id}")
        return self._attribute_data_to_obj(data[0] if data else None)
    
    def get_attribute_by_name(self, name: str) -> Attribute:
        name = text.norm(name)
        data = self._fetch_attributes_from_table(lambda h: f"name = {h|name}")
        return self._attribute_data_to_obj(data[0] if data else None)

    def _fetch_tasks_from_table(self, where: Callable[[queries.ArgHelper], str] | None, user: User | None) -> list[TaskResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT 
                    atu.task_id,
                    atu.user_id,
                    atu.attribute_id,
                    atu.idx,
                    atu.value,
                    MAX(atu.idx) AS max_idx
                FROM 
                    attribute_task_user AS atu
                JOIN 
                    attribute AS a ON atu.attribute_id = a.id
                WHERE 
                    t.list_id = {h|self.id}
                    AND atu.user_id {f"= {h|user.id}" if user is not None else f"!= {h|User.JUMPEDIA_USER.id}"}
                    {f"AND {where(h)}" if where is not None else ""}
                GROUP BY 
                    task_id,
                    attribute_id,
                    user_id;
            """, h.steal())

            result: list[TaskResultT] = cursor.fetchall()

        return result
    
    def _tasks_data_to_objs(self, data: list[TaskResultT]) -> dict[User, list[Task]]:
        if not data:
            return {}

        ATTRIBUTES = {attr.id: attr for attr in self.get_attributes()}

        get_user: dict[int, User] = {}
        get_task: dict[tuple[int, int], Task] = {}
        result: dict[User, list[Task]] = {}

        for row in data:
            user_id = row['user_id']

            if (user := get_user.get(user_id, None)) is None:
                user = User.get_other(self.community, user_id)
                get_user[user_id] = user
                result[user] = []

            task_id = row['task_id']
            user_task = (user_id, task_id)
            
            if (task := get_task.get(user_task, None)) is None:
                task = Task(
                    list=self, 
                    user=user, 
                    id=task_id, 
                    values={}
                )
                get_task[user_task] = task
                result[user].append(task)
            
            attribute = ATTRIBUTES[row['attribute_id']]
            value = pickle.loads(row['value'])

            value_list = task.values.setdefault(attribute, [value] * row['max_idx'])
            value_list[row['idx']] = value

        return result
            
    def get_tasks(self, where: Callable[[queries.ArgHelper], str] | None = None, user: User | None = User.JUMPEDIA_USER) -> dict[User, list[Task]]:
        return self._tasks_data_to_objs(self._fetch_tasks_from_table(where, user))

    def get_task_by_id(self, id: int, user: User | None = User.JUMPEDIA_USER) -> dict[User, Task]:
        result = self._tasks_data_to_objs(self._fetch_tasks_from_table(lambda h: f"task_id = {h|id}", user))

        if not result:
            raise fbe.TemporaryFeedbackError()
        
        return {user: tasks[0] for user, tasks in result.items() if tasks}
    
    def get_task_by_name(self, name: str, user: User | None = User.JUMPEDIA_USER) -> dict[User, Task]:
        result = self._tasks_data_to_objs(self._fetch_tasks_from_table(None, User.JUMPEDIA_USER))
        tasks: list[Task] = result[User.JUMPEDIA_USER]

        name = text.norm(name)
        task_id: int = -1

        for task in tasks:
            if task.values[self.name_attribute][0] == name:
                task_id = task.id
                break



            

    
    @classmethod
    def filter(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        ...

    @classmethod
    def sort(cls, list_: list[Task] | Self, expression: str) -> list[Task]:
        ...

        expression = text.fix_whitespace(expression, " ", True)

        parts = expression.split(" ")

        return []

