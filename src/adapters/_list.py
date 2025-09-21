from functools import cached_property
from typing import Final, overload, assert_never
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
from utils import argparsing, text
from discord import utils as dcutils

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

def _error_at_str(e: argparsing.UnexpectedCharError) -> str:
    SHOW_AROUND_CHARS: Final[int] = 10
    MORE: Final[str] = '...'

    start_from = e.i - SHOW_AROUND_CHARS
    end_at = e.i + SHOW_AROUND_CHARS
    parts: list[str] = ['```\n']

    if start_from > 0:
        start_from = 0
        parts.append(MORE)

    parts.append(e.s[start_from:e.i].replace('`', r'´'))

    if e.i >= len(e.s):
        parts.append(f"{e.s[e.i]} <<")
    else:
        parts.append(f" >> {e.s[e.i]} << ")

    parts.append(e.s[e.i:end_at + 1].replace('`', r'´'))
    
    if end_at < len(e.s):
        parts.append(MORE)

    return ''.join(parts)


def _parse_args(s: str) -> list[str]:
    try:
        return argparsing.parse_args(text.raw_to_real(s))
    except argparsing.UnexpectedCharError as e:
        assert isinstance(e.state, argparsing.ArgParseState)

        error_at = _error_at_str(e)

        if e.i >= len(e.s):
            match e.state:
                case argparsing.ArgParseState.IN_QUOTES:
                    raise feedbacks.temp(f"\" was never closed. {error_at}")
                
                case argparsing.ArgParseState.IN_ESCAPE:
                    raise feedbacks.temp(f"\\ must be followed by \" or \\, but text just ended. {error_at}")
                
        match e.state:
            case argparsing.ArgParseState.OUT_QUOTES_AFTER_COMMA:
                raise feedbacks.temp(f"Expected end of text or another argument wrapped in \", but got: {error_at}")
            
            case argparsing.ArgParseState.IN_QUOTES:
                raise feedbacks.temp(f"Expected text or \" to end the string, but got: {error_at}")
            
            case argparsing.ArgParseState.IN_ESCAPE:
                raise feedbacks.temp(f"Expected \\ or \" after \\, but got: {error_at}")
            
            case argparsing.ArgParseState.OUT_QUOTES_BEFORE_COMMA:
                raise feedbacks.temp(f"Expected end of text of , for next value, but got: {error_at}")
            
            case _:
                assert_never(e)

def _parse_kwargs(s: str) -> dict[text.NormStr, list[str]]:
    return argparsing.parse_kwargs(text.raw_to_real(s), text.raw_to_norm)

class ListAdapter(BaseAdapter):
    _list: List
    
    community: CommunityAdapter
    
    @property
    def real_name(self) -> str:
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
        aliases_set = frozenset(argparsing.parse_args(aliases))
        
        avm = {
            self.get_attribute(k).id: v for k, v in
            _parse_kwargs(attribute_value_mapping or '').items()
        }

        return TaskAdapter(
            self._list.create_task(name, aliases_set, ),
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
        attribute = _require_attribute_with_syn(text.raw_to_norm(syn), self._list)

        return _get_attribute_adapter(
            attribute,
            self
        )

    def get_task_attribute(self, syn: str) -> TaskAttributeAdapter:
        task_attribute = _require_task_attribute_with_syn(text.raw_to_norm(syn), self._list)
        return TaskAttributeAdapter(task_attribute, self)