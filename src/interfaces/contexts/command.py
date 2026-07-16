from dataclasses import dataclass

import discord

from services.attribute import (
    AttributePrepareService,
    AttributeQueryService,
    AttributeService,
)
from services.community import (
    CommunityPrepareService,
    CommunityQueryService,
    CommunityService,
)
from services.list import ListPrepareService, ListQueryService, ListService
from services.member import MemberService
from services.member_task import MemberTaskQueryService, MemberTaskService
from services.server import ServerService
from services.task import TaskPrepareService, TaskQueryService, TaskService
from services.user import UserService


@dataclass(frozen=True)
class PublicServices:
    server: ServerService
    community: CommunityService
    community_prepare: CommunityPrepareService
    community_query: CommunityQueryService
    list: ListService
    list_prepare: ListPrepareService
    list_query: ListQueryService
    attribute: AttributeService
    attribute_prepare: AttributePrepareService
    attribute_query: AttributeQueryService
    task: TaskService
    task_prepare: TaskPrepareService
    task_query: TaskQueryService
    member_task: MemberTaskService
    member_task_query: MemberTaskQueryService
    user: UserService
    member: MemberService


@dataclass(frozen=True)
class CommandContext:
    services: PublicServices
    interaction: discord.Interaction
