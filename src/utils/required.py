from types import UnionType
from typing import ClassVar, Never, Protocol
import discord as dc
import discordtools.feedbackerrors as fbe
from errors import FeedbackError
import structures
from structures.base_structure import BaseStructure
from structures.community.community import Community
from structures.list.list import List
from utils import text
from discordtools import messaging as msg

def structure_not_none[T: BaseStructure](obj: T | None, structure: structures.StructuresTypeT, name: str | None = None) -> T:
    if obj is not None:
        return obj
    
    structure_title = structures.human_join_structures_type(structure).title()
    structure_lower = {structures.human_join_structures_type(structure, str.lower)}
    
    raise FeedbackError(
        f"{structure_title} Not Found",
        (
            f"The {structure_lower} with the specified name {msg.shorten_and_code(name)} could not be found!"
            if name is not None else
            f"The required {structure_lower} could not be found!"
        )
    )

def server_not_none(server: dc.Guild | None) -> dc.Guild:
    if server is not None:
        return server
    
    raise fbe.TemporaryFeedbackError("You must be on a server to use this command")

def server_with_community(community: Community | None) -> Community:
    if community is not None:
        return community
    
    raise fbe.TemporaryFeedbackError("You must be on a server with a community on it")