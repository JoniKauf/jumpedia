from dataclasses import dataclass

from adapters.base_adapter import BaseAdapter
from structures.task import Task


@dataclass(frozen=True)
class _TaskAdapter(BaseAdapter[Task]):
    ...