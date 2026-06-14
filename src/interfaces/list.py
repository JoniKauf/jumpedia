from discord import app_commands
from domain.value_objects.list import ListName
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import messages


class ListInterface(BaseInterface, group_name="list"):
    @app_commands.command()
    @with_context()
    async def info(self, ctx: CommandContext, name: str) -> None:
        info_dto = ctx.services.list_query.info(ListName(name))

        data: dict[str, tuple[str, ...]] = {
            "Name": (info_dto.name.real.value,),
            "Is Default Selected List": ("True" if info_dto.is_default_selected_list else "False",),
            "Attributes": tuple(attr.name.real.value for attr in info_dto.attributes),
            "Task Count": (str(info_dto.task_count),),
        }

        await messages.object_info(ctx.interaction, type(info_dto), data)

    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext) -> None:
        ctx.services.list_query.info

    @app_commands.command()
    @with_context()
    async def create(self, ctx: CommandContext, name: str) -> None:
        lst = ctx.services.list.create(ListName(name))

        await messages.object_created(ctx.interaction, lst)