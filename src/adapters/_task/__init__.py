from dataclasses import dataclass

from adapters._base_adapter import BaseAdapter
from adapters._list._list import ListAdapter
from structures.list import List
from structures.task import Task
import builtins

@dataclass(frozen=True)
class TaskAdapter(BaseAdapter):
    _task: Task
    list: ListAdapter