

from dataclasses import dataclass
import json
from typing import Any, ClassVar
from adapters.base_adapter import BaseAdapter
from adapters.task_adapter import TaskAdapter
from errors.feedback import FeedbackError, feedbacks
from structures import attributes, task
from structures.attributes.task_attribute import TaskAttribute
from structures.list import List
from utils import parsetools, required, text
from discordtools import messaging as msg

@dataclass(frozen=True)
class ListAdapter(BaseAdapter[List]):
    alias_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=1,
        strict_type=list[str]
    )

    attribute_value_mapping_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=attributes.COLLECTION_MAX_DEPTH,
        strict_type=dict[str, attributes.ATTRIBUTE_VALUE_PARSE_TYPES]
    )
    
    def create_task(self, name: str, aliases: str, attribute_value_mapping: str | None) -> TaskAdapter:
        name = text.sanitize(name)
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

        unique_values_taken: dict[TaskAttribute, set[attributes.AttributeValueTypeT]] = {}

        for k, v in avm_parsed.items():
            k = text.sanitize(k)

            attr = required.structure_not_none(
                self._structure.get_task_attribute_by_name(k),
                TaskAttribute,
                k
            )

            value = attr.value_from_loaded(v)

            if attr.unique_value_per_list:
                for slot in value:
                    if self._structure.get_tasks()
            avm_result[attr] = value  
        
        return TaskAdapter(self.context, self._structure.create_task(
            name, 
            frozenset(aliases_set),
            avm_result
        ))
        
    def delete_task(self, name: str) -> None:
        name = text.sanitize(name)
        self._structure.delete_task(name)

    def create_task_attribute(self) -> :
        self._structure.create_task_attribute()