from adapters import BaseAdapter
from adapters._list import ListAdapter
from structures.attribute.task_attribute import TaskAttribute

class TaskAttributeAdapter(BaseAdapter):
    _task_attribute: TaskAttribute

    list: ListAdapter