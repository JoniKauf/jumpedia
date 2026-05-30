from dataclasses import dataclass
import discord

from interfaces.contexts.interacting_user import InteractingUserContext
from services.attribute import AttributeService
from services.community import CommunityQueryService, CommunityService
from services.list import ListService
from services.permission import PermissionService
from services.user import CommunityUserService, UserService


@dataclass(frozen=True)
class Services:
    permission: PermissionService
    user: UserService
    community_user: CommunityUserService
    community: CommunityService
    community_query: CommunityQueryService
    list: ListService
    attribute: AttributeService


@dataclass(frozen=True)
class CommandContext:
    services: Services
    interaction: discord.Interaction
    interacting_user_context: InteractingUserContext