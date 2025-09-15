from typing import overload, assert_never
from adapters import BaseAdapter, _attribute
from adapters._attribute.static_attribute import StaticAttributeAdapter
from adapters._attribute.task_attribute import TaskAttributeAdapter
from adapters._attribute.user_attribute import UserAttributeAdapter
from adapters._community import CommunityAdapter
from adapters._task import TaskAdapter
from errors.feedback import feedbacks
from structures import attribute
from structures.attribute.static_attribute import StaticAttribute
from structures.attribute.user_attribute import UserAttribute
from structures.task import Task
from structures.attribute.task_attribute import TaskAttribute
from structures.list import List
from utils import text
import shlex

@overload
def _get_attribute_adapter(attribute: StaticAttribute, list: 'ListAdapter') -> StaticAttributeAdapter:
    pass

@overload
def _get_attribute_adapter(attribute: TaskAttribute, list: 'ListAdapter') -> TaskAttributeAdapter:
    pass

@overload
def _get_attribute_adapter(attribute: UserAttribute, list: 'ListAdapter') -> UserAttributeAdapter:
    pass


def _get_attribute_adapter(attribute: attribute.AnyAttributeT, list: 'ListAdapter') -> _attribute.AnyAttributeAdapterT:
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

class ListAdapter(BaseAdapter):
    _list: List
    
    community: CommunityAdapter
    
    @property
    def name(self) -> str:
        return self._list.real_name

    # --- Task ---

    def get_tasks(self) -> list[TaskAdapter]:
        return [
            TaskAdapter(task, self)
            for task
            in self._list.get_tasks()
        ]
    
    def get_task(self, syn: str) -> TaskAdapter:
        return TaskAdapter(
            _require_task_with_syn(text.raw_to_norm(syn), self._list),
            self
        )

    def create_task(self, name: str, aliases: str, attribute_value_mapping: str | None) -> TaskAdapter:
        aliases_set = frozenset(shlex.split(aliases))
        
        return TaskAdapter(
            self._list.create_task(name, aliases_set, attribute_value_mapping),
            self
        )

    
    def delete_task(self, syn: str) -> None:
        task = self.get_task(_validate_and_get_real_and_norm_task_syn(syn))
        self._list.delete_task(task._task.id)

    def edit_task(self) -> None:
        ...
        # TODO: Make sure to check if unique value

    


    # --- Attribute ---

    def get_attributes(self) -> list[_attribute.AnyAttributeAdapterT]:
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._list.get_all_attributes_flat()
        ]
    
    def get_attribute(self, syn: str) -> _attribute.AnyAttributeAdapterT:
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