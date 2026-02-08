import types
import typing as t

from utils.orm import *
from utils.text import RealStr

if t.TYPE_CHECKING:
    from .attribute.slot_str import SlotStr
    from .jumpedia import Jumpedia
else:
    SlotStr = RealStr


class Community(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(str)
    def norm_name(self):
        pass

    @column(str)
    def real_name(self):
        pass

    @column(int, types.NoneType)
    def default_selected_list_id(self):
        pass

    @column(str)
    def limits(self):
        pass


class Server(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def community_id(self):
        pass


class JumpediaUser(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(str)
    def norm_name(self):
        pass

    @column(str)
    def raw_name(self):
        pass

    @column(int)
    def power(self):
        pass


# --- Per Community ---


class List(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def community_id(self):
        pass

    @column(str)
    def norm_name(self):
        pass

    @column(str)
    def real_name(self):
        pass


class CommunityUser(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def community_id(self):
        pass

    @column(int)
    def jumpedia_user_id(self):
        pass

    @column(int)
    def power(self):
        pass

    @column(int, types.NoneType)
    def selected_list_id(self):
        pass


# --- Static Attribute ---


class Attribute(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def type_id(self):
        pass

    @column(str)
    def norm_name(self):
        pass

    @column(str)
    def real_name(self):
        pass

    @column(int)
    def slot_type(self):
        pass

    @column(int)
    def position(self):
        pass

    @column(int)
    def min_slot_count(self):
        pass

    @column(int)
    def max_slot_count(self):
        pass

    @column(int, types.NoneType)
    def kind(self):
        pass


class AttributeAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def attribute_type_id(self):
        pass

    @column(str)
    def norm_alias(self):
        pass

    @column(str)
    def real_alias(self):
        pass


class AttributeCollectionEntry(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(str)
    def norm_slot(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass


class AttributeCollectionEntryAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_collection_entry_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(str)
    def norm_alias(self):
        pass

    @column(SlotStr)
    def slot_alias(self):
        pass


class Task(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(str)
    def norm_name(self):
        pass

    @column(SlotStr)
    def slot_name(self):
        pass


class TaskAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(str)
    def norm_alias(self):
        pass

    @column(SlotStr)
    def slot_alias(self):
        pass


class TaskAttributeValue(Model, table_name=SNAKE):
    @column(int)
    def list_id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass


class CommunityUserTask(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def community_user_id(self):
        pass


class CommunityUserTaskAttributeValue(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def community_user_task_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def community_user_id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass