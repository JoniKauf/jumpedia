from typing import TYPE_CHECKING
from adapters import BaseAdapter
from structures.task import Task

if TYPE_CHECKING:
    from adapters._list import ListAdapter


class TaskAdapter(BaseAdapter):
    _task: Task

    list: ListAdapter
