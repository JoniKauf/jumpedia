import discord
from discord import app_commands

from domain.entities.attribute import AttributeEntity
from domain.entities.task import TaskEntity
from domain.types.common import ID
from domain.types.user import UserID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.list import ListNameStr
from domain.value_objects.user import UserNameStr
from interfaces import dsl
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.enums.operation import OperationInterfaceEnum
from interfaces.message import format, messages
from services.dtos.task import TaskSummary
from services.dtos.user import UserRef


class TaskInterface(BaseInterface, group_name="task"):
    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        info = ctx.services.task_query.get_info(
            FieldSlotStr(task_name_or_alias),
            None if list_name is None else ListNameStr(list_name),
        )

        data: dict[str, tuple[str, ...]] = {
            str(info.static_attributes[0].name): (str(info.id),),
            str(info.static_attributes[1].name): (str(info.name),),
            str(info.static_attributes[2].name): tuple(
                str(alias) for alias in info.aliases
            ),
            **{
                str(attr.name): tuple(str(elem) for elem in v)
                for attr, v in info.field_mapping.items()
            },
        }

        await messages.object_info(ctx.interaction, type(info), data)

    @app_commands.command()
    @with_context()
    async def create(
        self,
        ctx: CommandContext,
        task_name: str,
        list_name: str,
        aliases: str | None = None,
        field_mapping: str | None = None,
    ) -> None:
        task = ctx.services.task.create(
            FieldSlotStr(task_name),
            ListNameStr(list_name),
            (
                ()
                if aliases is None
                else tuple(
                    FieldSlotStr(alias) for alias in dsl.list.engine.eval(aliases)
                )
            ),
            (
                {}
                if field_mapping is None
                else {
                    AttributeSynStr(k): tuple(FieldSlotStr(slot) for slot in v)
                    for k, v in dsl.mapping.engine.eval(field_mapping).items()
                }
            ),
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
            None if list_name is None else ListNameStr(list_name),
            (
                {}
                if user_field_mapping is None
                else {
                    AttributeSynStr(k): tuple(FieldSlotStr(slot) for slot in v)
                    for k, v in dsl.mapping.engine.eval(user_field_mapping).items()
                }
            ),
            (
                None
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
            None if list_name is None else ListNameStr(list_name),
            (
                None
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
        operation: OperationInterfaceEnum,
    ) -> None:
        after = tuple(
            FieldSlotStr(alias) for alias in dsl.list.engine.eval(new_task_aliases)
        )
        task = ctx.services.task.edit_aliases(
            FieldSlotStr(task_name), after, ListNameStr(list_name), operation.value
        )

        await messages.object_aliases_edited(ctx.interaction, task)


class TasksInterface(BaseInterface, group_name="tasks"):
    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext, list_name: str | None = None) -> None:
        summaries_data = ctx.services.task_query.get_summaries(
            None if list_name is None else ListNameStr(list_name)
        )

        summaries = summaries_data.summaries

        pre_data: dict[
            AttributeEntity.StaticT | AttributeEntity.TaskT, tuple[tuple[str, ...], ...]
        ] = {
            summaries_data.static_attributes[0]: tuple(
                (str(summary.id),) for summary in summaries
            ),
            summaries_data.static_attributes[1]: tuple(
                (str(summary.name),) for summary in summaries
            ),
            summaries_data.static_attributes[2]: tuple(
                tuple(str(alias) for alias in summary.aliases) for summary in summaries
            ),
            **{
                attr: tuple(
                    tuple(str(elem) for elem in summary.field_mapping.get(attr, ()))
                    for summary in summaries
                )
                for attr in summaries_data.task_attributes
            },
        }

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            str(attr.name): v
            for attr, v in sorted(
                pre_data.items(), key=lambda item: item[0].position.value
            )
        }

        await messages.object_browse(ctx.interaction, TaskSummary, data)
