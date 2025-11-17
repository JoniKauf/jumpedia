import typing as t

from structures.attribute.slot_str import SlotStr
from structures.task import Task

from . import BaseAdapter

if t.TYPE_CHECKING:
    from adapters._list import ListAdapter


class TaskAdapter(BaseAdapter[Task]):
    list: ListAdapter

    @property
    def name(self) -> SlotStr:
        return self._s.slot_name
