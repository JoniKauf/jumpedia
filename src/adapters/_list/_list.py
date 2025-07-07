

from dataclasses import dataclass
import json
from typing import Any, ClassVar
from adapters._base_adapter import BaseAdapter
from adapters._community import CommunityAdapter
from adapters._task import TaskAdapter
from errors.feedback import FeedbackError, feedbacks
from structures import attributes, task
from structures.task import Task
from structures.attributes.task_attribute import TaskAttribute
from structures.list import List
from utils import parsetools
from discordtools import messaging as msg


def _require_task_with_name(name: str, list: List) -> Task:
    task = list.get_task_by_name(name)

    if task is None:
        raise feedbacks.temp(f"Task with name `{name}` not found!")
    
    return task

def _valnitize_task_name(name: str) -> str:
    from utils import text
    return text.valnitize(name, task.MAX_SYN_LEN, task.MAX_SYN_LEN)

@dataclass(frozen=True)
class ListAdapter(BaseAdapter):
    _list: List
    
    community: CommunityAdapter
    
    alias_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=1,
        strict_type=[str]
    )

    attribute_value_mapping_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=attributes.COLLECTION_MAX_DEPTH,
        strict_type={str: attributes.ATTRIBUTE_VALUE_PARSE_TYPES}
    )
    
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
    
    def get_task(self, name: str) -> TaskAdapter:
        return TaskAdapter(
            _require_task_with_name(_valnitize_task_name(name), self._list),
            self
        )

    def create_task(self, name: str, aliases: str, attribute_value_mapping: str | None) -> TaskAdapter:
        name = _valnitize_task_name(name)
        aliases_parsed: list[str] = self.__class__.alias_parser.loads(aliases)

        name, aliases_set = text.validate_and_sanitize_syns(
            name, 
            aliases_parsed, 
            task.MAX_SYN_LEN,
            attributes.MAX_ALIAS_COUNT + 1
        )

        avm_result: dict[TaskAttribute[Any], list[attributes.AttributeValueTypeT]] = {}

        avm_parsed: dict[str, attributes.AttributeValueParseTypesT] = self.__class__.attribute_value_mapping_parser.loads(
            attribute_value_mapping or parsetools.EMPTY_JSON_OBJ
        )

        unique_values_used: dict[TaskAttribute, set[attributes.AttributeValueTypeT]] = {}

        for k, v in avm_parsed.items():
            k = text.sanitize(k)

            attr = required.structure_not_none(
                self._list.get_task_attribute_by_name(k),
                TaskAttribute,
                k
            )

            value = attr.value_from_loaded(v)

            if attr.uniqueness >= attributes.UniquenessExtended.PER_LIST:
                unique_values_used[attr] = unique = set()
                
                # TODO
                for slot in value:
                    
                    unique.add(slot)

            avm_result[attr] = value  
        
        return TaskAdapter(self.context, self._structure.create_task(
            name, 
            frozenset(aliases_set),
            avm_result
        ))
    
    def delete_task(self, name: str) -> None:
        name = text.sanitize(name)
        self._structure.delete_task(name)

    def edit_task(self) -> None:
        ...
        # TODO: Make sure to check if unique value

    def create_task_attribute(self) -> :
        self._structure.create_task_attribute()