from string.templatelib import Template

from discord import app_commands
from interfaces.command import groups
from message import format

from domain.entities.attribute import AttributeEntity
from domain.entities.list import ListEntity
from domain.entities.task import TaskEntity
from domain.value_objects.list import ListNameStr
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import messages
from services.dtos.list import ListSummary


class ListInterface(BaseInterface, group_name="list"):
    edit_group = groups.create_edit_group()

    @app_commands.command()
    @with_context()
    async def info(self, ctx: CommandContext, list_name: str) -> None:
        info = ctx.services.list_query.get_info(ListNameStr(list_name))

        data: dict[str, tuple[str, ...]] = {
            "Name": (str(info.name),),
            "Is Default Selected List": (
                "True" if info.is_default_selected_list else "False",
            ),
            "Attributes": tuple(str(attr.name) for attr in info.attributes),
            "Task Count": (str(info.task_count),),
        }

        await messages.object_info(ctx.interaction, type(info), data)

    @app_commands.command()
    @with_context()
    async def create(self, ctx: CommandContext, list_name: str) -> None:
        lst = ctx.services.list.create(ListNameStr(list_name))

        await messages.object_created(ctx.interaction, lst)

    @app_commands.command()
    @with_context()
    async def nuke(self, ctx: CommandContext, list_name: str) -> None:
        prepared, community, lst = ctx.services.list_prepare.delete(
            ListNameStr(list_name)
        )

        consequences: Template = (
            t"All {format.type_name_for_body(TaskEntity, False)} and {format.type_name_for_body(AttributeEntity, False)} of this specific {format.type_name_for_body(ListEntity)} will be deleted! This also includes their sub-data like fields, user fields, collections and more!"
        )

        await messages.nuke_object_on_confirmation(
            ctx.interaction,
            to_nuke=lst,
            parent=community,
            consequences=consequences,
            execute=lambda: ctx.services.list.delete(prepared),
        )

    @edit_group.command(name="name")
    @with_context()
    async def edit_name(
        self, ctx: CommandContext, list_name: str, new_list_name: str
    ) -> None:
        after = ListNameStr(new_list_name)
        before = ctx.services.list.edit_name(ListNameStr(list_name), after)

        await messages.object_name_edited(ctx.interaction, ListEntity, before, after)


class ListsInterface(BaseInterface, group_name="lists"):
    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext) -> None:
        summaries = ctx.services.list_query.get_summaries()

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            "Name": tuple((str(summary.name),) for summary in summaries),
            "Is Default Selected List": (
                tuple(
                    ("True" if summary.is_default_selected_list else "False",)
                    for summary in summaries
                )
            ),
            "Attributes": tuple(
                tuple(str(attr.name) for attr in summary.attributes)
                for summary in summaries
            ),
            "Task Count": tuple((str(summary.task_count),) for summary in summaries),
        }

        await messages.object_browse(ctx.interaction, ListSummary, data)
