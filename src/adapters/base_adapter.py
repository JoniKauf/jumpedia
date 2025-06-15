
from dataclasses import dataclass

from adapters.context import Context
from structures.base_structure import BaseStructure


@dataclass(frozen=True)
class BaseAdapter[T: BaseStructure]:
    context: Context
    _structure: T