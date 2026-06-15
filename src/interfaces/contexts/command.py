from dataclasses import dataclass

import discord

from services.attribute import AttributeService
from services.community import CommunityQueryService, CommunityService
from services.list import ListQueryService, ListService
from services.server import ServerService


@dataclass(frozen=True)
class PublicServices:
    server: ServerService
    community: CommunityService
    community_query: CommunityQueryService
    list: ListService
    list_query: ListQueryService
    attribute: AttributeService


@dataclass(frozen=True)
class CommandContext:
    services: PublicServices
    interaction: discord.Interaction
