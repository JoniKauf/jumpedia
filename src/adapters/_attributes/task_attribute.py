from dataclasses import dataclass

from adapters._base_adapter import BaseAdapter
from adapters._list import ListAdapter
from structures.attributes.task_attribute import TaskAttribute


@dataclass(frozen=True)
class TaskAttributeAdapter(BaseAdapter):
    _task_attribute: TaskAttribute

    list: ListAdapter