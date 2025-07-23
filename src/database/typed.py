from types import NoneType
from typing import Union, overload
from database.simple_orm import SNAKE, BaseModel, column

class Community(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(str)
    def name(self): pass
    @column((int, NoneType))
    def default_selected_list_id(self): pass

class Server(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(int)
    def community_id(self): pass

class JumpediaUser(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(str)
    def name(self): pass
    @column(int)
    def power(self): pass

# --- Per Community ---

class List(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(int)
    def community_id(self): pass
    @column(str)
    def name(self): pass

class CommunityUser(BaseModel, table_name=SNAKE):
    @column(int)
    def community_id(self): pass
    @column(int)
    def user_id(self): pass
    @column(int)
    def power(self): pass
    @column(int)
    def selected_list_id(self): pass


# --- Base Attribute ---

class BaseAttribute(BaseModel, table_name=None):
    @column(int)
    def id(self): pass
    @column(int)
    def list_id(self): pass
    @column(str)
    def name(self): pass
    @column(int)
    def slot_type(self): pass
    @column(int)
    def position(self): pass
    @column(int)
    def min_slots(self): pass
    @column(int)
    def max_slots(self): pass
    @column(int)
    def uniqueness(self): pass


class BaseAttributeAlias(BaseModel, table_name=None):
    @column(int)
    def id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(int)
    def list_id(self): pass
    @column(str)
    def alias(self): pass


class BaseCollectionAttributeCollectionNode(BaseModel, table_name=None):
    @column(int)
    def id(self): pass
    @column(int)
    def parent_id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(bytes)
    def value(self): pass
    @column(int)
    def sort_value(self): pass

class BaseCollectionAttributeCollectionNodeAlias(BaseModel, table_name=None):
    @column(int)
    def id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(int)
    def attribute_collection_node_id(self): pass
    @column(bytes)
    def alias(self): pass

class BaseAttributeTaskValue(BaseModel, table_name=None):
    @column(int)
    def task_id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(int)
    def index(self): pass
    @column(bytes)
    def slot(self): pass


# --- Static Attribute ---

class StaticAttribute(BaseAttribute, table_name=SNAKE):
    pass

class StaticAttributeAlias(BaseAttributeAlias, table_name=SNAKE):
    pass

# --- Task Attribute ---

class TaskAttribute(BaseAttribute, table_name=SNAKE):
    pass

class TaskAttributeAlias(BaseAttributeAlias, table_name=SNAKE):
    pass

class TaskAttributeCollectionNode(BaseCollectionAttributeCollectionNode, table_name=SNAKE):
    pass

class TaskAttributeCollectionNodeAlias(BaseCollectionAttributeCollectionNodeAlias, table_name=SNAKE):
    pass


# --- User Attribute ---

class UserAttribute(BaseAttribute, table_name=SNAKE):
    pass

class UserAttributeAlias(BaseAttributeAlias, table_name=SNAKE):
    pass

class UserAttributeCollectionNode(BaseCollectionAttributeCollectionNode, table_name=SNAKE):
    pass

class UserAttributeCollectionNodeAlias(BaseCollectionAttributeCollectionNodeAlias, table_name=SNAKE):
    pass


# --- Task ---

class Task(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(int)
    def list_id(self): pass
    @column(str)
    def name(self): pass

class TaskAlias(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(int)
    def task_id(self): pass
    @column(int)
    def list_id(self): pass
    @column(str)
    def alias(self): pass

class TaskAttributeTaskValueNotUnique(BaseAttributeTaskValue, table_name=SNAKE):
    pass

class TaskAttributeTaskValueUniquePerValue(BaseAttributeTaskValue, table_name=SNAKE):
    pass

class TaskAttributeTaskValueUniquePerAttribute(BaseAttributeTaskValue, table_name=SNAKE):
    pass

class BaseUserAttributeTaskValue(BaseAttributeTaskValue, table_name=None):
    @column(int)
    def user_id(self): pass

class UserAttributeTaskValueNotUnique(BaseUserAttributeTaskValue, table_name=SNAKE):
    pass

class UserAttributeTaskValueUniquePerValue(BaseUserAttributeTaskValue, table_name=SNAKE):
    pass

class UserAttributeTaskValueUniquePerAttribute(BaseUserAttributeTaskValue, table_name=SNAKE):
    pass