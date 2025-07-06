
from dataclasses import dataclass, field
from typing import Any

import discord as dc


@dataclass(frozen=True)
class BaseAdapter:
    _cache: dict[str, Any] = field(init=False, default_factory=dict)