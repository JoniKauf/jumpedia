import ast
from dataclasses import astuple, dataclass, field
import sys
from threading import RLock
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Iterable, Literal, Optional, Self, Sequence, TypeAlias, TypedDict, cast, get_args, TYPE_CHECKING
from database import queries
from discordtools import feedbackerrors as fbe
from trickjump import attribute
from trickjump.community import Community
from trickjump.trickjump import Trickjump
from utils import text

class ListTableT(TypedDict):
    id: int
    name: str
    display_name: str
    community_id: int

@dataclass(frozen=True)
class List:
    id: int
    name: str
    display_name: str
    community: Community
    
    TABLE_NAME: ClassVar[str] = "list"
    MAX_NAME_LENGTH: ClassVar[int] = 50

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, List) and self.id == value.id