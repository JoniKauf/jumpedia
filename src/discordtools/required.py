from types import UnionType
from typing import ClassVar, Never, Protocol
import discord as dc
import discordtools.feedbackerrors as fbe
from errors import feedback
import structures
from structures.abstract_structure import StructureBase
from structures.community.community import Community
from structures.list.list import List
from utils import text


def structure_name_not_found[T: StructureBase](obj: T | None, name: str, structures: structures.StructuresTypeT) -> T:
    if obj is not None:
        return obj
    
    raise feedback.StructuresNotFound(name, structures)

def structure_not_found[T: StructureBase](obj: T | None, type: StructureTypeT) -> T:
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