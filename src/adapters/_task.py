from adapters import BaseAdapter
from adapters._list import ListAdapter
from structures.task import Task

class TaskAdapter(BaseAdapter):
    _task: Task
    
    list: ListAdapter