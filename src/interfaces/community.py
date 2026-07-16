import datetime as dt
import typing as t
from dataclasses import asdict

import discord
from discord import app_commands

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.task import TaskEntity
from domain.enums.rank import CommunityRank
from domain.sentinels.default import DEFAULT
from domain.types.common import ID
from domain.types.user import UserID
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.string import Str
from domain.value_objects.user import UserNameStr
from interfaces.attribute import ListNameStr
from interfaces.base import BaseInterface
from interfaces.command import groups
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import format, messages
from services.dtos.community import CommunitySummary
from services.dtos.user import UserRef

_DEFAULT_LIMITS: t.Final[CommunityLimits] = CommunityLimits.default()

class CommunityInterface(BaseInterface, group_name="community"):
    edit_group = groups.create_edit_group()

    @app_commands.command()
    @with_context()
    async def info(self, ctx: CommandContext, community: str | None = None) -> None:
        info = ctx.services.community_query.get_info(
            DEFAULT if community is None else CommunityNameStr(community)
        )

        data: dict[str, tuple[str, ...]] = {
            "Name": (str(info.name),),
            "Created": (str(info.created_at),),
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
        field_slot_count_max: int = _DEFAULT_LIMITS.field_slot_count_max,
        collection_entry_count_max: int = _DEFAULT_LIMITS.collection_entry_count_max,
        collection_entry_alias_count_max: int = _DEFAULT_LIMITS.collection_entry_alias_count_max,
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
                field_slot_count_max=field_slot_count_max,
                collection_entry_count_max=collection_entry_count_max,
                collection_entry_alias_count_max=collection_entry_alias_count_max,
            ),
        )

        await messages.object_created(ctx.interaction, community)

    @app_commands.command()
    @with_context()
    async def nuke(
        self,
        ctx: CommandContext,
    ) -> None:
        prepared, community = ctx.services.community_prepare.delete()

        await messages.nuke_object_on_confirmation(
            ctx.interaction,
            to_nuke=community,
            parent=None,
            consequences=t"Literally every piece of information about this community will be deleted! This includes all {format.type_name_for_body(ListEntity, False)}, {format.type_name_for_body(AttributeEntity, False)}, {format.type_name_for_body(TaskEntity, False)} and more...\n**This is the ultimate hammer of destruction!**",
            execute=lambda: ctx.services.community.delete(prepared),
        )

    @edit_group.command(name="default_selected_list")
    @with_context()
    async def edit_default_selected_list(
        self, ctx: CommandContext, list_name: str | None = None
    ) -> None:
        community, lst = ctx.services.community.edit_default_selected_list(
            None if list_name is None else ListNameStr(list_name)
        )

        await messages.success(
            ctx.interaction,
            t"Default Selected {format.type_name_for_header(ListEntity)} Edited",
            t"The default selected {format.type_name_for_body(ListEntity)} of the {format.mention_body(community)} has been "
            + (t"unsed" if lst is None else t"changed to {format.mention_body(lst)}")
            + t" successfully!",
        )


class CommunitiesInterface(BaseInterface, group_name="communities"):
    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext) -> None:
        summaries = ctx.services.community_query.get_summaries()

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            "Name": tuple((str(summary.name),) for summary in summaries),
            "Created": tuple(
                (str(summary.created),) for summary in summaries
            ),
            "User Count": tuple((str(summary.member_count),) for summary in summaries),
            "List Count": tuple((str(summary.list_count),) for summary in summaries),
            "Total Task Count": tuple(
                (str(summary.total_task_count),) for summary in summaries
            ),
        }

        await messages.object_browse(ctx.interaction, CommunitySummary, data)
