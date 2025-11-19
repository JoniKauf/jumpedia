import typing as t

from structures.attribute.slot_str import SlotStr
from structures.task import Task

from . import BaseAdapter, BaseStructureAdapter

if t.TYPE_CHECKING:
    from ._list import ListAdapter


class TaskAdapter(BaseStructureAdapter[Task]):
    list: ListAdapter

    @property
    def name(self) -> SlotStr:
        return self._s.slot_name
