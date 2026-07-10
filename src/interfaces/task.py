import typing as t

import discord
from discord import app_commands

from domain.entities.attribute import AttributeEntity
from domain.entities.task import TaskEntity
from domain.sentinels.default import DEFAULT
from domain.types.common import ID
from domain.types.field_mapping import FieldMappingRawT
from domain.types.user import UserID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.list import ListNameStr
from domain.value_objects.user import UserNameStr
from interfaces import dsls
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.enums.edit_mode import (
    AliasEditModeInterfaceEnum,
    FieldMappingEditModeInterfaceEnum,
)
from interfaces.message import format, messages
from services.dtos.user import UserRef


def _field_mapping_input_to_value(
    s: str | None,
) -> FieldMappingRawT:
    return tuple(
        ()
        if s is None
        else tuple(
            (AttributeSynStr(k), tuple(FieldSlotStr(slot) for slot in v))
            for k, v in dsls.mapping.engine.eval(s)
        )
    )


def _aliases_input_to_value(s: str | None) -> tuple[FieldSlotStr, ...]:
    return (
        ()
        if s is None
        else tuple(FieldSlotStr(alias) for alias in dsls.list.engine.eval(s))
    )


class TaskInterface(BaseInterface, group_name="task"):
    @app_commands.command()
    @with_context()
    async def info_user(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        info = ctx.services.task_query.get_info(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_info(
            ctx.interaction,
            TaskEntity,
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
        aliases: str,
        field_mapping: str,
    ) -> None:
        task = ctx.services.task.create(
            FieldSlotStr(task_name),
            ListNameStr(list_name),
            _aliases_input_to_value(aliases),
            _field_mapping_input_to_value(field_mapping),
        )

        await messages.object_created(ctx.interaction, task)

    @app_commands.command()
    @with_context()
    async def nuke(self, ctx: CommandContext, task_name: str, list_name: str) -> None:
        deleted = ctx.services.task.delete(
            FieldSlotStr(task_name), ListNameStr(list_name)
        )

        await messages.object_nuked(ctx.interaction, deleted)

    @app_commands.command()
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

        await messages.object_name_edited(ctx.interaction, TaskEntity, before, after)

    @app_commands.command()
    @with_context()
    async def edit_aliases(
        self,
        ctx: CommandContext,
        task_name: str,
        new_task_aliases: str,
        list_name: str,
        edit_mode: AliasEditModeInterfaceEnum,
    ) -> None:
        after = tuple(
            FieldSlotStr(alias) for alias in dsls.list.engine.eval(new_task_aliases)
        )
        task = ctx.services.task.edit_aliases(
            after, edit_mode.value, FieldSlotStr(task_name), ListNameStr(list_name)
        )

        await messages.object_aliases_edited(ctx.interaction, task)

    @app_commands.command()
    @with_context()
    async def edit_field_mapping(
        self,
        ctx: CommandContext,
        task_name: str,
        list_name: str,
        new_user_field_mapping: str,
        edit_mode: FieldMappingEditModeInterfaceEnum,
    ) -> None:
        task = ctx.services.task.edit_field_mapping(
            _field_mapping_input_to_value(new_user_field_mapping),
            edit_mode.value,
            FieldSlotStr(task_name),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.success(
            ctx.interaction,
            t"{format.type_name_for_header(type(task))} Field Mapping Edited",
            t"The field mapping of the {format.mention_body(task)} was successfully edited!",
        )

    # --- Member Task --- #

    @app_commands.command()
    @with_context()
    async def info_of_user(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        info = ctx.services.member_task_query.get_info(
            FieldSlotStr(task_name_or_alias),
            (
                DEFAULT
                if user is None
                else UserRef(UserID(ID(user.id)), UserNameStr(user.name))
            ),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_info(
            ctx.interaction,
            TaskEntity,
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
        user_field_mapping: str | None = None,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        member, task = ctx.services.member_task.give_to_user(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
            (_field_mapping_input_to_value(user_field_mapping)),
            (
                DEFAULT
                if user is None
                else UserRef(UserID(ID(user.id)), UserNameStr(user.name))
            ),
        )

        await messages.success(
            ctx.interaction,
            t"{format.type_name_for_header(TaskEntity)} Given",
            t"The {format.mention_body(task)} has been given to the {format.mention_body(member)} successfully!",
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
            (
                DEFAULT
                if user is None
                else UserRef(UserID(ID(user.id)), UserNameStr(user.name))
            ),
        )

        await messages.success(
            ctx.interaction,
            t"{format.type_name_for_header(TaskEntity)} Taken",
            t"The {format.mention_body(task)} has been taken from the {format.mention_body(member)} successfully!",
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
            _field_mapping_input_to_value(new_user_field_mapping),
            edit_mode.value,
            (
                DEFAULT
                if user is None
                else UserRef(UserID(ID(user.id)), UserNameStr(user.name))
            ),
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.success(
            ctx.interaction,
            t"Given {format.type_name_for_header(type(task))} Updated",
            t"The {format.mention_body(task)} the {format.mention_body(member)} had already given themselves was updated successfully!",
        )


class TasksInterface(BaseInterface, group_name="tasks"):
    @app_commands.command()
    @with_context()
    async def browse(
        self,
        ctx: CommandContext,
        sort_dsl: str | None = None,
        list_name: str | None = None,
    ) -> None:
        summaries = ctx.services.task_query.get_summaries(
            (
                ()
                if sort_dsl is None
                else tuple(
                    (AttributeSynStr(sort), asc)
                    for sort, asc in dsls.sort.engine.eval(sort_dsl)
                )
            ),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_browse(
            ctx.interaction,
            TaskEntity,
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
        sort_dsl: str | None = None,
        list_name: str | None = None,
    ) -> None:
        summaries = ctx.services.member_task_query.get_summaries(
            (
                ()
                if sort_dsl is None
                else tuple(
                    (AttributeSynStr(sort), asc)
                    for sort, asc in dsls.sort.engine.eval(sort_dsl)
                )
            ),
            (
                DEFAULT
                if user is None
                else UserRef(UserID(ID(user.id)), UserNameStr(user.name))
            ),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_browse(
            ctx.interaction,
            TaskEntity,
            {
                str(attr.name): tuple(
                    tuple(str(slot) for slot in field) for field in fields
                )
                for attr, fields in summaries.items()
            },
        )
