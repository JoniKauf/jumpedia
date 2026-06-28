from discord import app_commands

from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context


class TaskInterface(BaseInterface, group_name="task"):
    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        ctx.services.community_query


class TasksInterface(BaseInterface, group_name="tasks"):
    pass
