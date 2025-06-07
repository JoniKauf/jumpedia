from types import UnionType
from typing import ClassVar, Never, Protocol
import discord as dc
import discordtools.feedbackerrors as fbe
from structures.attribute import AnyAttributeT
from structures.community import Community
from structures.list import List
from structures.task import Task
from utils import text


class RequiredStructureName(Protocol):
    STRUCTURE_NAME: ClassVar[str]


def obj_generic[T: RequiredStructureName](obj: T | None, type: type[T] | tuple[type[T], *tuple[type[T], ...]]) -> T:
    if obj is not None:
        return obj
    
    if not isinstance(type, tuple):
        type_name = type.STRUCTURE_NAME
    else:
        type_name = text.human_join(tuple(t.STRUCTURE_NAME for t in type), text.FinalDelimiter.OR)
        
    raise fbe.TemporaryFeedbackError(f"The specified {type_name.lower()} could not be found!")

def server_generic(server: dc.Guild | None) -> dc.Guild:
    if server is not None:
        return server
    
    raise fbe.TemporaryFeedbackError("You must be on a server to use this command")

def server_with_community(community: Community | None) -> Community:
    if community is not None:
        return community
    
    raise fbe.TemporaryFeedbackError("You must be on a server with a community on it")