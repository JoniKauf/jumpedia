from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
import json
from typing import TYPE_CHECKING, AbstractSet, Any, Callable, ClassVar, Iterable, Literal, Never, NotRequired, Self, TypedDict

from database import queries 
from structures.base_structure import BaseStructure
from structures.attributes import AnyAttributeT, AttributeValueType, AttributeValueTypeT
from structures.attributes import collection
from structures.attributes.abstract_attribute import BaseAttribute
from structures.attributes.collection import CollectionNode, CollectionNodesT
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute
from structures.list import UserCollectionNodeT, UserCollectionNodesT
from structures.task import Task
from utils import metautils, parsetools, text
from structures import attributes, task
from database import typed as typed
from database.typed import Tables as TBL
import structures.list as list_package


import pickle

if TYPE_CHECKING:
    from structures.community import Community


MAX_NAME_LENGTH: int = 64
MAX_ATTRIBUTES: int = 3
MAX_TASKS: int = 1


class UserCollectionNodeT(TypedDict, total=True):
    value: str
    aliases: list[str]
    sort_value: int
    nodes: NotRequired[list['UserCollectionNodeT']]
    
type UserCollectionNodesT = list[UserCollectionNodeT]