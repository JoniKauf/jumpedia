from dataclasses import dataclass

import discord

from services.attribute import AttributeQueryService, AttributeService
from services.community import CommunityQueryService, CommunityService
from services.list import ListQueryService, ListService
from services.member import MemberService
from services.member_task import MemberTaskQueryService, MemberTaskService
from services.server import ServerService
from services.task import TaskQueryService, TaskService
from services.user import UserService


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
    member_task: MemberTaskService
    member_task_query: MemberTaskQueryService
    user: UserService
    member: MemberService


@dataclass(frozen=True)
class CommandContext:
    services: PublicServices
    interaction: discord.Interaction
