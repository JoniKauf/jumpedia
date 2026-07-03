import datetime as dt
import typing as t
from dataclasses import asdict

import discord
from discord import app_commands

from domain.enums.rank import CommunityRank
from domain.types.common import ID
from domain.types.user import UserID
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.string import Str
from domain.value_objects.user import UserNameStr
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import messages
from services.dtos.community import CommunitySummary
from services.dtos.task import UserRef

_DEFAULT_LIMITS: t.Final[CommunityLimits] = CommunityLimits.default()


def _created_to_representation(created: dt.datetime) -> str:
    return created.strftime("%A, %Y/%m/%d %H:%M:%S")


class CommunityInterface(BaseInterface, group_name="community"):
    @app_commands.command()
    @with_context()
    async def info(self, ctx: CommandContext, community: str | None = None) -> None:
        info = ctx.services.community_query.get_info(
            None if community is None else CommunityNameStr(community)
        )

        data: dict[str, tuple[str, ...]] = {
            "Name": (str(info.name),),
            "Created": (_created_to_representation(info.created),),
            "Owners": tuple(
                str(user.name)
                for user in info.members
                if user.community_rank is CommunityRank.OWNER
            ),
            "User Count": (str(len(info.members)),),
            "Lists": tuple(str(lst.name) for lst in info.lists),
            "Default Selected List": (
                (str(info.default_selected_list.name),)
                if info.default_selected_list
                else ()
            ),
            "Total Task Count": (str(info.total_task_count),),
        }

        data |= {
            "Limit - " + name.replace("_", " ").title(): (str(value),)
            for name, value in asdict(info.limits).items()
            if isinstance(value, int)
        }

        await messages.object_info(ctx.interaction, type(info), data)

    @app_commands.command()
    @with_context()
    async def create(
        self,
        ctx: CommandContext,
        community_name: str,
        community_owner: discord.User,
        community_list_count_max: int = _DEFAULT_LIMITS.community_list_count_max,
        list_attribute_count_max: int = _DEFAULT_LIMITS.list_attribute_count_max,
        list_task_count_max: int = _DEFAULT_LIMITS.list_task_count_max,
        attr_alias_count_max: int = _DEFAULT_LIMITS.attribute_alias_count_max,
        attr_task_value_slot_count_max: int = _DEFAULT_LIMITS.field_slot_count_max,
        attr_coll_entry_count_max: int = _DEFAULT_LIMITS.collection_entry_count_max,
        attr_coll_entry_alias_count_max: int = _DEFAULT_LIMITS.collection_entry_alias_count_max,
    ) -> None:
        community = ctx.services.community.create(
            CommunityNameStr(community_name),
            UserRef(
                UserID(ID(community_owner.id)),
                UserNameStr(community_owner.name),
            ),
            CommunityLimits(
                community_list_count_max=community_list_count_max,
                list_attribute_count_max=list_attribute_count_max,
                list_task_count_max=list_task_count_max,
                attribute_alias_count_max=attr_alias_count_max,
                field_slot_count_max=attr_task_value_slot_count_max,
                collection_entry_count_max=attr_coll_entry_count_max,
                collection_entry_alias_count_max=attr_coll_entry_alias_count_max,
            ),
        )

        await messages.object_created(ctx.interaction, community)

    @app_commands.command()
    @with_context()
    async def nuke(
        self,
        ctx: CommandContext,
    ) -> None:
        deleted = ctx.services.community.delete()

        await messages.object_nuked(ctx.interaction, deleted)


class CommunitiesInterface(BaseInterface, group_name="communities"):
    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext) -> None:
        summaries = ctx.services.community_query.get_summaries()

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            "Name": tuple((str(summary.name),) for summary in summaries),
            "Created": tuple(
                (_created_to_representation(summary.created),) for summary in summaries
            ),
            "User Count": tuple(
                (str(summary.member_count),) for summary in summaries
            ),
            "List Count": tuple((str(summary.list_count),) for summary in summaries),
            "Total Task Count": tuple(
                (str(summary.total_task_count),) for summary in summaries
            ),
        }

        await messages.object_browse(ctx.interaction, CommunitySummary, data)
