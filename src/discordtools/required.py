import discord as dc
import discordtools.feedbackerrors as fbe
from structures.community import Community
from structures.list import List

def server(server: dc.Guild | None) -> dc.Guild:
    if server is not None:
        return server
    
    raise fbe.TemporaryFeedbackError("You must be in a server")

def community_this_server(community: Community | None) -> Community:
    if community is not None:
        return community
    
    raise fbe.TemporaryFeedbackError("You must be in a server with a community on it")

def community_general(community: Community | None) -> Community:
    if community is not None:
        return community
    
    raise fbe.TemporaryFeedbackError("The specified community could not be found!")


def list(list: List | None) -> List:
    if list is not None:
        return list
    
    raise fbe.TemporaryFeedbackError("The specified list could not be found!")