from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import cached_property
import json
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Literal, NotRequired, Self, TypedDict

import mariadb

from database import queries
from discordtools import feedbackerrors as fbe
from utils import metautils, parsetools, text

from database import strong as S
from database.strong import Tables as T

import pickle

from structures.user import User

from structures.attribute import AbstractAttribute, AnyAttributeT, AttributeValueTypeT, CollectionTreeItem, CollectionTreeT, StaticAttribute, TaskAttribute, AttributeValueType, UserAttribute
from structures.task import Task
from utils.locked import equality_locked

if TYPE_CHECKING:
    from structures.community import Community


# --- Collection Types --- #

class UserCollectionTreeItemT(TypedDict, total=True):
    value: str
    alias: list[str]
    sort_value: int
    children: NotRequired[list['UserCollectionTreeItemT']]
type UserCollectionTreeT = list[UserCollectionTreeItemT]

type UserCollectionT = None | UserCollectionTreeT


def _parse_user_collection[T: AttributeValueTypeT](
    str_user_collection: str, 
    value_type: AttributeValueType[T],
) -> CollectionT[T]:
    user_value_collection: UserCollectionT = parsetools.json_loads_safe(
        str_user_collection, 
        AbstractAttribute.COLLECTION_MAX_DEPTH
    )

    if user_value_collection is None:
        return []
    
    if not isinstance(user_value_collection, list):
        raise fbe.TemporaryFeedbackError("Not a tree")
    
    tree = _parse_user_collection_tree(user_value_collection, value_type)

    _add_roots(tree, None)

    return tree

def _add_roots[T: AttributeValueTypeT](
    tree: CollectionTreeT[T],
    root: CollectionTreeItem[T] | None
) -> None:
    for item in tree:
        object.__setattr__(item, 'root', root)  # CHANGE IF VARNAME CHANGES

        _add_roots(item.nodes, item)

def _parse_user_collection_tree[T: AttributeValueTypeT](
    user_collection_tree: UserCollectionTreeT, 
    value_type: AttributeValueType[T]
) -> CollectionTreeT[T]:
    result: CollectionTreeT = []

    for item in user_collection_tree:
        value, alias, sort_value = _extract_data_from_collection_item(item, value_type)

        sub_trees = item.get('children', [])

        if not isinstance(sub_trees, list):
            raise fbe.TemporaryFeedbackError("Not a sub tree")
        
        item = CollectionTreeItem(
            value,
            alias,
            sort_value,
            _parse_user_collection_tree([sub_tree for sub_tree in sub_trees], value_type)
        )

        result.append(item)

    return result

def _extract_data_from_collection_item[T: AttributeValueTypeT](
    item: UserCollectionTreeItemT,
    value_type: AttributeValueType[T]
) -> tuple[T, frozenset[T], int]:
    try:
        sort_value: int = int(item['sort_value'])
    except KeyError as e:
        raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
    except ValueError as e:
        raise fbe.TemporaryFeedbackError("Not an int")
        
    AbstractAttribute.generic_number_valid(sort_value)

    try:
        bad_value = item['value']
    except KeyError as e:
        raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
    
    try:
        bad_alias = item.get('alias', [])

        if not isinstance(bad_alias, list):
            raise TypeError()
    except TypeError:
        raise fbe.TemporaryFeedbackError(f"Not a list of aliases")
    
    value: T = AbstractAttribute._from_str_singular(bad_value, value_type)

    alias = set(
        norm_for_collection(AbstractAttribute._from_str_singular(a, value_type)) 
        for a in frozenset(bad_alias)
    )
    
    normed_value: T = norm_for_collection(value)
    
    if normed_value in alias:
        alias.remove(normed_value)

    return (value, frozenset(alias), sort_value)


@dataclass(frozen=True, kw_only=True)
class List:
    MAX_NAME_LENGTH: ClassVar[int] = 64
    MAX_ATTRIBUTES: ClassVar[int] = 1
    MAX_TASKS: ClassVar[int] = 1

    INVALID_ENDING: ClassVar[str] = __name__.lower()

    community: 'Community'
    id: int
    name: str

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
    
    def _attribute_creation_generic[T: AttributeValueTypeT](
        self,
        bad_name: str,
        bad_aliases: Iterable[str],
        min_slots: int,
        max_slots: int,
    ) -> tuple[str, frozenset[str], int]:
        with equality_locked(self):
            attributes = self.get_attributes()
            
            if len(attributes) >= self.__class__.MAX_ATTRIBUTES:
                raise fbe.TemporaryFeedbackError("Max attributes reached")
        
            
            if not (1 <= max_slots <= AbstractAttribute.MAX_SLOTS):
                raise fbe.TemporaryFeedbackError()

            if not (0 <= min_slots <= max_slots):
                raise fbe.TemporaryFeedbackError()
            
            index = max(attr.index for attr in attributes) + 1

            return (name, frozenset(aliases), index)
        

    # --- Static Attribute ---

    def create[T: AttributeValueTypeT](
        self,
        name: str,
        value_type: AttributeValueType[T],
        user_collection: CollectionTreeT,
        min_slots: int,
        max_slots: int,
        unique_slots: bool,
        unique_value_per_list: bool
    ):
        """This method should not public to the user!"""
        
        

    def _fetch_static_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[S.TableResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {T.StaticAttribute}
                WHERE 
                    {T.StaticAttribute.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[S.TableResultT] = cursor.fetchall()

        return result
    
    def _static_attribute_data_to_obj(self, data: S.TableResultT) -> StaticAttribute:
        SAT = T.StaticAttribute

        return StaticAttribute(
            list=self,
            id=data[SAT.id],
            name=data[SAT.name],
            index=data[SAT.index],
            collection
        )
    
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