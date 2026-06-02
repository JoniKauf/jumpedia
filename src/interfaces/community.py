from discord import app_commands
import discord
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import messages
from interfaces.message.format import Mention
import typing as t

_DEFAULT_LIMITS: t.Final[Limits] = Limits.default()


class CommunityInterface(BaseInterface, group_name="community"):
    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, community_name: str | None = None
    ) -> None:
        community_info = ctx.services.community_query.info(None if community_name is None else CommunityName(community_name))

        await messages.object_info(
            ctx.interaction,
            t"Community Info"
        )

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
        community = ctx.services.community.create(
            CommunityName(name),
            ID(owner.id),
            StrStore(owner.name),
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

        await messages.object_created(ctx.interaction, community)

    @app_commands.command()
    @with_context()
    async def nuke(
        self,
        ctx: CommandContext,
    ) -> None:
        community_dto = ctx.services.community.delete()

        await messages.object_nuked(ctx.interaction, community_dto)