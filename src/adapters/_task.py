import typing as t

from structures.task import Task

from . import BaseAdapter

if t.TYPE_CHECKING:
    from adapters._list import ListAdapter


class TaskAdapter(BaseAdapter[Task]):
    list: ListAdapter
