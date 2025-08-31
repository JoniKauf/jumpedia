from types import NoneType
from typing import Union, overload
from database.simple_orm import SNAKE, BaseModel, column

class Community(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(str)
    def norm_name(self): pass
    @column(str)
    def real_name(self): pass
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
    def norm_name(self): pass
    @column(str)
    def real_name(self): pass
    @column(int)
    def power(self): pass

# --- Per Community ---

class List(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(int)
    def community_id(self): pass
    @column(str)
    def norm_name(self): pass
    @column(str)
    def real_name(self): pass

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
    def norm_name(self): pass
    @column(str)
    def real_name(self): pass
    @column(int)
    def slot_type(self): pass
    @column(int)
    def position(self): pass
    @column(int)
    def min_slots(self): pass
    @column(int)
    def max_slots(self): pass


class BaseAttributeAlias(BaseModel, table_name=None):
    @column(int)
    def id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(int)
    def list_id(self): pass
    @column(str)
    def norm_alias(self): pass
    @column(str)
    def real_alias(self): pass


class BaseAttributeCollectionEntry(BaseModel, table_name=None):
    @column(int)
    def id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(int)
    def index(self): pass
    @column(str)
    def norm_slot(self): pass
    @column(str)
    def real_slot(self): pass

class BaseAttributeCollectionEntryAlias(BaseModel, table_name=None):
    @column(int)
    def id(self): pass
    @column(int)
    def attribute_collection_entry_id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(str)
    def norm_alias(self): pass
    @column(str)
    def real_alias(self): pass

class BaseAttributeTaskValue(BaseModel, table_name=None):
    @column(int)
    def task_id(self): pass
    @column(int)
    def attribute_id(self): pass
    @column(int)
    def index(self): pass
    @column(str)
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

class TaskAttributeCollectionSlot(BaseAttributeCollectionEntry, table_name=SNAKE):
    pass

class TaskAttributeCollectionSlotAlias(BaseAttributeCollectionEntryAlias, table_name=SNAKE):
    pass


# --- User Attribute ---

class UserAttribute(BaseAttribute, table_name=SNAKE):
    pass

class UserAttributeAlias(BaseAttributeAlias, table_name=SNAKE):
    pass

class UserAttributeCollectionSlot(BaseAttributeCollectionEntry, table_name=SNAKE):
    pass

class UserAttributeCollectionSlotAlias(BaseAttributeCollectionEntryAlias, table_name=SNAKE):
    pass


# --- Task ---

class Task(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(int)
    def list_id(self): pass
    @column(str)
    def norm_name(self): pass
    @column(str)
    def real_name(self): pass

class TaskAlias(BaseModel, table_name=SNAKE):
    @column(int)
    def id(self): pass
    @column(int)
    def task_id(self): pass
    @column(int)
    def list_id(self): pass
    @column(str)
    def norm_alias(self): pass
    @column(str)
    def real_alias(self): pass

class TaskAttributeTaskValue(BaseAttributeTaskValue, table_name=SNAKE):
    pass

class UserAttributeTaskValue(BaseAttributeTaskValue, table_name=SNAKE):
    @column(int)
    def user_id(self): pass