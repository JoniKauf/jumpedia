from types import UnionType
from typing import ClassVar, Never, Protocol
import discord as dc
import discordtools.feedbackerrors as fbe
from errors import feedback
import structures
from structures.base_structure import BaseStructure
from structures.community.community import Community
from structures.list.list import List
from utils import text


def structure_with_name[T: BaseStructure](obj: T | None, name: str, structures: structures.StructuresTypeT) -> T:
    if obj is not None:
        return obj
    
    raise feedback.StructuresNotFound(structures, name)

def structure_not_none[T: BaseStructure](obj: T | None, structures: structures.StructuresTypeT) -> T:
    if obj is not None:
        return obj
    
    raise feedback.StructuresNotFound(structures)
    
def user_on_server(user: dc.User | dc.Member) -> dc.Guild:
    if isinstance(user, dc.Member):
        return user.guild
    
    raise fbe.TemporaryFeedbackError("You must be on a server to use this command")

def server_with_community(community: Community | None) -> Community:
    if community is not None:
        return community
    
    raise fbe.TemporaryFeedbackError("You must be on a server with a community on it")