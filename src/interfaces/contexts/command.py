from dataclasses import dataclass

import discord

from services.attribute import AttributeQueryService, AttributeService
from services.community import CommunityQueryService, CommunityService
from services.list import ListQueryService, ListService
from services.server import ServerService
from services.task import TaskQueryService, TaskService


@dataclass(frozen=True)
class PublicServices:
    server: ServerService
    community: CommunityService
    community_query: CommunityQueryService
    list: ListService
    list_query: ListQueryService
    attribute: AttributeService
    attribute_query: AttributeQueryService
    task: TaskService
    task_query: TaskQueryService


@dataclass(frozen=True)
class CommandContext:
    services: PublicServices
    interaction: discord.Interaction
