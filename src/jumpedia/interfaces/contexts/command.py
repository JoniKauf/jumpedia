from dataclasses import dataclass

import discord

from jumpedia.services.attribute import (
    AttributePrepareService,
    AttributeQueryService,
    AttributeService,
)
from jumpedia.services.community import (
    CommunityPrepareService,
    CommunityQueryService,
    CommunityService,
)
from jumpedia.services.list import ListPrepareService, ListQueryService, ListService
from jumpedia.services.member import MemberQueryService, MemberService
from jumpedia.services.member_task import MemberTaskQueryService, MemberTaskService
from jumpedia.services.server import ServerService
from jumpedia.services.task import TaskPrepareService, TaskQueryService, TaskService
from jumpedia.services.user import UserService


@dataclass(frozen=True, slots=True)
class PublicServices:
    attribute: AttributeService
    attribute_prepare: AttributePrepareService
    attribute_query: AttributeQueryService
    community: CommunityService
    community_prepare: CommunityPrepareService
    community_query: CommunityQueryService
    list: ListService
    list_prepare: ListPrepareService
    list_query: ListQueryService
    member: MemberService
    member_query: MemberQueryService
    member_task: MemberTaskService
    member_task_query: MemberTaskQueryService
    server: ServerService
    task: TaskService
    task_prepare: TaskPrepareService
    task_query: TaskQueryService
    user: UserService


@dataclass(frozen=True, slots=True)
class CommandContext:
    services: PublicServices
    interaction: discord.Interaction
