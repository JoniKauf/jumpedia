
from dataclasses import dataclass, field
from typing import Any

import discord as dc
from adapters.context import Context
from structures.base_structure import BaseStructure


@dataclass(frozen=True)
class BaseAdapter[T: BaseStructure | None]:
    _interaction: dc.Interaction
    _structure: T

    _cache: dict[str, Any] = field(init=False, default_factory=dict)