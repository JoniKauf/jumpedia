from dataclasses import asdict

from discord import app_commands
import discord
from domain.enums.rank import CommunityRank
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import messages
import typing as t

from services.dtos.community import CommunitySummaryDTO

_DEFAULT_LIMITS: t.Final[CommunityLimits] = CommunityLimits.default()


class CommunityInterface(BaseInterface, group_name="community"):
    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, community_name: str | None = None
    ) -> None:
        info_dto = ctx.services.community_query.info(
            None if community_name is None else CommunityName(community_name)
        )

        data: dict[str, tuple[str, ...]] = {
            "Name": (info_dto.name.real.value,),
            "Created": (info_dto.created.strftime("%A, %Y/%m/%d %H:%M:%S"),),
            "Owners": tuple(
                user.name.real.value
                for user in info_dto.community_users
                if user.community_rank is CommunityRank.OWNER
            ),
            "User Count": (str(len(info_dto.community_users)),),
            "Lists": tuple(lst.name.real.value for lst in info_dto.lists),
            "Default Selected List": (
                (info_dto.default_selected_list.name.real.value,)
                if info_dto.default_selected_list
                else ()
            ),
            "Total Task Count": (str(info_dto.total_task_count),),
        }

        data |= {
            "Limit - " + name.replace("_", " ").title(): (str(value),)
            for name, value in asdict(info_dto.limits).items()
            if isinstance(value, int)
        }

        await messages.object_info(ctx.interaction, type(info_dto), data)

    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext) -> None:
        summaries = ctx.services.community_query.summaries()

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            "Name": tuple((summary.name.real.value,) for summary in summaries),
            "Created": tuple(
                (summary.created.strftime("%A, %Y/%m/%d %H:%M:%S"),)
                for summary in summaries
            ),
            "User Count": tuple(
                (str(summary.community_user_count),) for summary in summaries
            ),
            "List Count": tuple((str(summary.list_count),) for summary in summaries),
            "Total Task Count": tuple(
                (str(summary.total_task_count),) for summary in summaries
            ),
        }

        await messages.object_browse(ctx.interaction, CommunitySummaryDTO, data)

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
            CommunityLimits(
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
