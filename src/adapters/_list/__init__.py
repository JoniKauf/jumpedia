

from dataclasses import dataclass
import json
from typing import Any, ClassVar, overload, assert_never
from adapters import _attributes
from adapters._attributes.static_attribute import StaticAttributeAdapter
from adapters._attributes.task_attribute import TaskAttributeAdapter
from adapters._attributes.user_attribute import UserAttributeAdapter
from adapters._base_adapter import BaseAdapter
from adapters._community import CommunityAdapter
from adapters._task import TaskAdapter
from errors.feedback import FeedbackError, feedbacks
from structures import attribute, task
from structures.attribute import collection
from structures.attribute.static_attribute import StaticAttribute
from structures.attribute.user_attribute import UserAttribute
from structures.task import Task
from structures.attribute.task_attribute import TaskAttribute
from structures.list import List
from utils import parsetools, text
from discordtools import messaging as msg


@overload
def _get_attribute_adapter(attribute: StaticAttribute, list: 'ListAdapter') -> StaticAttributeAdapter:
    pass

@overload
def _get_attribute_adapter(attribute: TaskAttribute, list: 'ListAdapter') -> TaskAttributeAdapter:
    pass

@overload
def _get_attribute_adapter(attribute: UserAttribute, list: 'ListAdapter') -> UserAttributeAdapter:
    pass


def _get_attribute_adapter(attribute: attribute.AnyAttributeT, list: 'ListAdapter') -> _attributes.AnyAttributeAdapterT:
    if isinstance(attribute, StaticAttribute):
        return StaticAttributeAdapter(attribute, list)
    
    if isinstance(attribute, TaskAttribute):
        return TaskAttributeAdapter(attribute, list)
    
    if isinstance(attribute, UserAttribute):
        return UserAttributeAdapter(attribute, list)
    
    assert_never(attribute)

    
def _require_task_with_syn(norm_syn: text.NormStr, list: List) -> Task:
    task = list.get_task_by_syn(norm_syn)

    if task is None:
        raise feedbacks.temp(f"Task with name or alias `{norm_syn}` not found!")
    
    return task

def _require_attribute_with_syn(norm_syn: text.NormStr, list: List) -> attribute.AnyAttributeT:
    attribute = list.get_attribute_by_syn(TaskAttribute, norm_syn)

    if attribute is None:
        raise feedbacks.temp(f"Attribute with name or alias `{norm_syn}` not found!")
    
    return attribute

def _require_task_attribute_with_syn(syn: text.NormStr, list: List) -> TaskAttribute:
    attribute = list.get_attribute_by_syn(TaskAttribute, syn)

    if attribute is None:
        raise feedbacks.temp(f"Task attribute with name or alias `{syn}` not found!")
    
    return attribute


def _validate_and_get_real_and_norm_task_syn(name: str) -> tuple[text.RealStr, text.NormStr]:
    return text.raw_to_real_and_validate(name, , task.MAX_SYN_LEN)

def _validate_and_get_real_and_norm_attribute_syn(syn: str) -> str:
    return text.raw_to_real_and_validate(syn, attribute.MIN_SYN_LEN, attribute.MAX_SYN_LEN)


ALIAS_PARSER: parsetools.SafeJsonParser[list[str]] = parsetools.SafeJsonParser(
    max_depth=1,
    strict_type=[str]
)

ATTRIBUTE_VALUE_MAPPING_PARSER: parsetools.SafeJsonParser[dict[str, attribute.AttributeValueParseTypesT]] = parsetools.SafeJsonParser(
    max_depth=collection.MAX_DEPTH,
    strict_type={str: attribute.ATTRIBUTE_VALUE_PARSE_TYPES}
)


@dataclass(frozen=True)
class ListAdapter(BaseAdapter):
    _list: List
    
    community: CommunityAdapter
    
    @property
    def name(self) -> str:
        return self._list.name

    # --- Task ---

    def get_tasks(self) -> list[TaskAdapter]:
        return [
            TaskAdapter(task, self)
            for task
            in self._list.get_tasks()
        ]
    
    def get_task(self, syn: str) -> TaskAdapter:
        return TaskAdapter(
            _require_task_with_syn(_validate_and_get_real_and_norm_task_syn(syn), self._list),
            self
        )

    def create_task(self, name: str, aliases: str, attribute_value_mapping: str | None) -> TaskAdapter:
        
        return TaskAdapter(
            self._list.create_task(name, aliases_parsed, avm_final),
            self
        )

    
    def delete_task(self, syn: str) -> None:
        task = self.get_task(_validate_and_get_real_and_norm_task_syn(syn))
        self._list.delete_task(task._task.id)

    def edit_task(self) -> None:
        ...
        # TODO: Make sure to check if unique value

    


    # --- Attribute ---

    def get_attributes(self) -> list[_attributes.AnyAttributeAdapterT]:
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._list.get_all_attributes_flat()
        ]
    
    def get_attribute(self, syn: str) -> _attributes.AnyAttributeAdapterT:
        attribute = _require_attribute_with_syn(_validate_and_get_real_and_norm_attribute_syn(syn), self._list)

        return _get_attribute_adapter(
            attribute,
            self
        )

    def get_task_attribute(self, syn: str) -> TaskAttributeAdapter:
        task_attribute = _require_task_attribute_with_syn(_validate_and_get_real_and_norm_attribute_syn(syn), self._list)
        return TaskAttributeAdapter(task_attribute, self)

    def create_task_attribute(self) -> TaskAttributeAdapter:
        self._list.create_task_attribute()