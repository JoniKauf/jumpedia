

from dataclasses import dataclass
from typing import Any

from adapters.base_adapter import BaseAdapter
from structures.attributes import AnyAttributeT


@dataclass(frozen=True)
class AttributeAdapter[T: AnyAttributeT[Any]](BaseAdapter[T]):
    pass