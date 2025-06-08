from types import UnionType
from typing import ClassVar, Never, Protocol
import discord as dc
from discordtools.errors import FeedbackError
import discordtools.feedbackerrors as fbe
from structures.community import Community
from structures.list import List
from structures.task import Task
from utils import text


class RequiredStructureName(Protocol):
    STRUCTURE_NAME: ClassVar[str]

type StructureTypeT[T: RequiredStructureName] = type[T] | tuple[type[T], *tuple[type[T], ...]]


def _structure_types_to_str[T: RequiredStructureName](type: StructureTypeT[T]) -> str:
    if not isinstance(type, tuple):
        return type.STRUCTURE_NAME
    else:
        return text.human_join(
            tuple(t.STRUCTURE_NAME for t in type),
            " or "
        )

def structure_name_not_found[T: RequiredStructureName](obj: T | None, name: str, type: StructureTypeT) -> T:
    if obj is not None:
        return obj
    
    type_str = _structure_types_to_str(type)
        
    raise FeedbackError(
        header=f"{type_str.title()} Not Found",
        description=f"The {type_str.lower()} with the name `{name}` could not be found!"
    )

def structure_not_found[T: RequiredStructureName](obj: T | None, type: StructureTypeT) -> T:
    if obj is not None:
        return obj
    
    type_str = _structure_types_to_str(type)
        
    raise FeedbackError(
        header=f"{type_str.title()} Not Found",
        description=f"The {type_str.lower()} could not be found!"
    )
    
def server_generic(server: dc.Guild | None) -> dc.Guild:
    if server is not None:
        return server
    
    raise fbe.TemporaryFeedbackError("You must be on a server to use this command")

def server_with_community(community: Community | None) -> Community:
    if community is not None:
        return community
    
    raise fbe.TemporaryFeedbackError("You must be on a server with a community on it")