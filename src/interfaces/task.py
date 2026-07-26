import discord
from discord import app_commands

from domain.entities.task import TaskEntity
from domain.enums.concept import Concept
from domain.enums.edit_mode import AliasEditMode, FieldMappingEditMode
from domain.sentinels.default import DEFAULT
from domain.typing.common import ID
from domain.typing.user import UserID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.list import ListNameStr
from domain.value_objects.user import UserNameStr
from interfaces import bindings
from interfaces.base import BaseInterface
from interfaces.bindings import user_ref
from interfaces.command import cogs, groups
from interfaces.contexts.command import CommandContext
from interfaces.decorators.with_context import with_context
from interfaces.enums.edit_mode import (
    AliasEditModeInterfaceEnum,
    FieldMappingEditModeInterfaceEnum,
)
from interfaces.message import messages
from interfaces.message.formatting import F


class TaskInterface(
    BaseInterface, group_name=cogs.cog_concept_to_group_name(Concept.TASK, plural=False)
):
    edit_group = groups.create_edit_group()

    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        info = ctx.services.task_query.get_info(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_info(
            ctx.interaction,
            Concept.TASK,
            {
                str(attr.name): tuple(str(slot) for slot in field)
                for attr, field in info.items()
            },
        )

    @app_commands.command()
    @with_context()
    async def create(
        self,
        ctx: CommandContext,
        task_name: str,
        list_name: str,
        aliases_dsl_sequence: str,
        field_mapping_dsl: str,
    ) -> None:
        task = ctx.services.task.create(
            FieldSlotStr(task_name),
            ListNameStr(list_name),
            bindings.sequence.task_aliases(aliases_dsl_sequence),
            bindings.mapping.field_mapping(field_mapping_dsl),
        )

        await messages.object_created(ctx.interaction, task)

    @app_commands.command()
    @with_context()
    async def nuke(self, ctx: CommandContext, task_name: str, list_name: str) -> None:
        prepared, lst, task = ctx.services.task_prepare.delete(
            FieldSlotStr(task_name), ListNameStr(list_name)
        )

        await messages.nuke_object_on_confirmation(
            ctx.interaction,
            to_nuke=task,
            parent=lst,
            consequences=t"All its associated field and user field data will be deleted!",
            execute=lambda: ctx.services.task.delete(prepared),
        )

    @edit_group.command(name="name")
    @with_context()
    async def edit_name(
        self,
        ctx: CommandContext,
        task_name: str,
        new_task_name: str,
        list_name: str,
    ) -> None:
        after = FieldSlotStr(new_task_name)
        before = ctx.services.task.edit_name(
            FieldSlotStr(task_name), after, ListNameStr(list_name)
        )

        await messages.object_name_edited(ctx.interaction, Concept.TASK, before, after)

    @edit_group.command(name="aliases")
    @with_context()
    async def edit_aliases(
        self,
        ctx: CommandContext,
        task_name: str,
        new_task_aliases_dsl_sequence: str,
        list_name: str,
        edit_mode: AliasEditModeInterfaceEnum,
    ) -> None:
        after = bindings.sequence.task_aliases(new_task_aliases_dsl_sequence)
        task = ctx.services.task.edit_aliases(
            after,
            AliasEditMode(edit_mode.value),
            FieldSlotStr(task_name),
            ListNameStr(list_name),
        )

        await messages.object_aliases_edited(ctx.interaction, task)

    @edit_group.command(name="field_mapping")
    @with_context()
    async def edit_field_mapping(
        self,
        ctx: CommandContext,
        task_name: str,
        list_name: str,
        new_user_field_mapping_dsl: str,
        edit_mode: FieldMappingEditModeInterfaceEnum,
    ) -> None:
        task = ctx.services.task.edit_field_mapping(
            bindings.mapping.field_mapping(new_user_field_mapping_dsl),
            FieldMappingEditMode(edit_mode.value),
            FieldSlotStr(task_name),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.TASK)} {F.format(Concept.FIELD_MAPPING)} Edited",
            t"The field mapping of the {F.full_mention(task)} was successfully edited!",
        )

    # --- Member Task --- #

    @app_commands.command()
    @with_context()
    async def info_user(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        info = ctx.services.member_task_query.get_info(
            FieldSlotStr(task_name_or_alias),
            user_ref.user_ref(user),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_info(
            ctx.interaction,
            Concept.TASK,
            {
                str(attr.name): tuple(str(slot) for slot in field)
                for attr, field in info.items()
            },
        )

    @app_commands.command()
    @with_context()
    async def give(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        user_field_mapping_dsl: str | None = None,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        member, task = ctx.services.member_task.give_to_user(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
            bindings.mapping.field_mapping(user_field_mapping_dsl),
            user_ref.user_ref(user),
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.TASK)} Given",
            t"The {F.full_mention(task)} has been given to the {F.full_mention(member)} successfully!",
        )

    @app_commands.command()
    @with_context()
    async def take(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        member, task = ctx.services.member_task.take_from_user(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
            user_ref.user_ref(user),
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.TASK)} Taken",
            t"The {F.full_mention(task)} has been taken from the {F.full_mention(member)} successfully!",
        )

    @app_commands.command()
    @with_context()
    async def update_given(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        new_user_field_mapping: str,
        edit_mode: FieldMappingEditModeInterfaceEnum,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        member, task = ctx.services.member_task.edit_member_field_mapping(
            bindings.mapping.field_mapping(new_user_field_mapping),
            FieldMappingEditMode(edit_mode.value),
            user_ref.user_ref(user),
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.success(
            ctx.interaction,
            t"Given {F.format(Concept.TASK)} Updated",
            t"The {F.full_mention(task)} the {F.full_mention(member)} had already given themselves was updated successfully!",
        )


class TasksInterface(
    BaseInterface, group_name=cogs.cog_concept_to_group_name(Concept.TASK, plural=True)
):
    @app_commands.command()
    @with_context()
    async def browse(
        self,
        ctx: CommandContext,
        filter_dsl: str | None = None,
        sort_dsl: str | None = None,
        yield_dsl_sequence: str | None = None,
        list_name: str | None = None,
    ) -> None:
        summaries = ctx.services.task_query.get_summaries(
            bindings.filter.filter(filter_dsl),
            bindings.sort.sorts(sort_dsl),
            bindings.sequence.yield_(yield_dsl_sequence),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_browse(
            ctx.interaction,
            Concept.TASK,
            {
                str(attr.name): tuple(
                    tuple(str(slot) for slot in field) for field in fields
                )
                for attr, fields in summaries.items()
            },
        )

    # --- Member Task --- #

    @app_commands.command()
    @with_context()
    async def browse_user(
        self,
        ctx: CommandContext,
        user: discord.User | None = None,
        filter_dsl: str | None = None,
        sort_dsl: str | None = None,
        yield_dsl_sequence: str | None = None,
        list_name: str | None = None,
    ) -> None:
        summaries = ctx.services.member_task_query.get_summaries(
            bindings.filter.filter(filter_dsl),
            bindings.sort.sorts(sort_dsl),
            bindings.sequence.yield_(yield_dsl_sequence),
            user_ref.user_ref(user),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_browse(
            ctx.interaction,
            Concept.TASK,
            {
                str(attr.name): tuple(
                    tuple(str(slot) for slot in field) for field in fields
                )
                for attr, fields in summaries.items()
            },
        )
