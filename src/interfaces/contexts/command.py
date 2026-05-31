from dataclasses import dataclass
import discord

from services.attribute import AttributeService
from services.community import CommunityQueryService, CommunityService
from services.list import ListService


@dataclass(frozen=True)
class PublicServices:
    community: CommunityService
    community_query: CommunityQueryService
    list: ListService
    attribute: AttributeService


@dataclass(frozen=True)
class CommandContext:
    services: PublicServices
    interaction: discord.Interaction