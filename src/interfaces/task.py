from discord import app_commands

from domain.entities.attribute import AttributeEntity
from domain.value_objects.list import ListNameStr
from domain.value_objects.field_slot import FieldSlotStr
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.message import messages
from services.dtos.task import TaskSummary


class TaskInterface(BaseInterface, group_name="task"):
    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        info = ctx.services.task_query.info(
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
        self, ctx: CommandContext, task_name: str, list_name: str, aliases: str | None = None, field_mapping: str | None = None
    ) -> None:
        task = ctx.services.task.create(FieldSlotStr(task_name), ListNameStr(list_name), aliases, field_mapping)

    @app_commands.command()
    @with_context()
    async def give(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        ...


class TasksInterface(BaseInterface, group_name="tasks"):
    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext, list_name: str | None = None) -> None:
        summaries_data = ctx.services.task_query.summaries(
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
                    tuple(
                        str(elem)
                        for elem in summary.field_mapping.get(attr, ())
                    )
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
