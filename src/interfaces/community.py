from discord import app_commands
import discord
from domain.enums.rank import MetaRank
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import messages
from repositories.user import UserEntity
from services.community import CommunityService
from services.list import ListService
from services.user import UserService
from sqlalchemy.orm import Session
import typing as t

_DEFAULT_LIMITS: t.Final[Limits] = Limits.default()


class CommunityInterface(BaseInterface, group_name="community"):
    def __init__(
        self, community_service: CommunityService, user_service: UserService
    ) -> None:
        super().__init__()
        self.community_service = community_service
        self.user_service = user_service

    @app_commands.command()
    @with_context()
    async def create(
        self,
        ctx: CommandContext,
        name: str,
        owner: discord.User,
        community_list_count_max: int = _DEFAULT_LIMITS.community_list_count_max,
        list_attribute_count_max: int = _DEFAULT_LIMITS.list_attribute_count_max,
        list_task_count_max: int = _DEFAULT_LIMITS.list_task_count_max,
        attr_alias_count_max: int = _DEFAULT_LIMITS.attribute_alias_count_max,
        attr_task_value_slot_count_max: int = _DEFAULT_LIMITS.attribute_task_value_slot_count_max,
        attr_coll_entry_count_max: int = _DEFAULT_LIMITS.attribute_collection_entry_count_max,
        attr_coll_entry_alias_count_max: int = _DEFAULT_LIMITS.attribute_collection_entry_alias_count_max,
    ) -> None:
        community = self.community_service.create(
            self.user_service.get_or_create(
                UserEntity(ctx.member.id, StrStore(ctx.member.name))
            ),
            StrStore(name),
            ctx.member.guild.id,
            self.user_service.get_or_create(UserEntity(owner.id, StrStore(owner.name))),
            Limits(
                community_list_count_max=community_list_count_max,
                list_attribute_count_max=list_attribute_count_max,
                list_task_count_max=list_task_count_max,
                attribute_alias_count_max=attr_alias_count_max,
                attribute_task_value_slot_count_max=attr_task_value_slot_count_max,
                attribute_collection_entry_count_max=attr_coll_entry_count_max,
                attribute_collection_entry_alias_count_max=attr_coll_entry_alias_count_max,
            ),
        )

        await messages.created(ctx.interaction, community)

    
    @app_commands.command()
    @with_context()
    async def nuke(
        self,
        ctx: CommandContext,
    ) -> None:
        ...

