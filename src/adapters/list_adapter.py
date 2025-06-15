

from dataclasses import dataclass
import json
from typing import Any
from adapters.base_adapter import BaseAdapter
from adapters.task_adapter import TaskAdapter
from errors.feedback import FeedbackError, feedbacks
from structures import attributes, task
from structures.list import List
from utils import parsetools, text
from discordtools import messaging as msg

@dataclass(frozen=True)
class ListAdapter(BaseAdapter[List]):
    def create_task(self, name: str, aliases: str, attribute_value_mapping: str | None) -> TaskAdapter:
        name = text.sanitize(name)

        name, aliases_set = text.validate_and_sanitize_syns(
            name, 
            parsetools.json_loads_safe(aliases, 1), 
            task.MAX_SYN_LEN,
            attributes.MAX_ALIAS_COUNT + 1
        )

        MAX_DEPTH: int = 2
        
        try:
            avm_loaded: Any = parsetools.json_loads_safe(attribute_value_mapping, MAX_DEPTH)
        except json.JSONDecodeError as e:
            raise feedbacks.invalid_attribute_value_mapping(
                "The issue is that the value does not represent valid JSON text. "
                f"At {msg.code(f"...{e.msg[e.pos:32]}...")} it started failing."
            )
        except RecursionError:
            raise feedbacks.invalid_attribute_value_mapping(
                "The issue is that the max depth was exceeded. In this case it "
                f"should be a mapping of text to lists, so the max depth is {MAX_DEPTH}."
            )
        except Exception:
            raise feedbacks.invalid_attribute_value_mapping(
                "The issue is unknown. There was an error in parsing the specified text, "
                "so try looking for some oddities or weird symbols in your input."
            )
        if not isinstance(avm_loaded, dict):
            raise feedbacks.invalid_attribute_value_mapping(
                "The issue is that it does not represent a JSON object, "
                "which means the most outer layer should be surrounded in `{...}`."
            )
        
        # TODO
        return self._structure.create_task(
            name, 
            frozenset(aliases_set),
            attribute_value_mapping
        )
        
    def delete_task(self, name: str) -> None:
        name = text.sanitize(name)
        self._structure.delete_task(name)

    def create_task_attribute(self) -> :
        self._structure.create_task_attribute()