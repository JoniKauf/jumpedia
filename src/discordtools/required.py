import discord as dc
import discordtools.feedbackerrors as fbe
from structures.community import Community

def server(server: dc.Guild | None) -> dc.Guild:
    if server is not None:
        return server
    
    raise fbe.TemporaryFeedbackError("You must be in a server")

def community(community: Community | None) -> Community:
    if community is not None:
        return community
    
    raise fbe.TemporaryFeedbackError("You must be in a server with a community on it")
