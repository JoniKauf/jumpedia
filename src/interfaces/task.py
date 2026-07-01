from discord import app_commands

from domain.enums.attribute import AttributeKind
from domain.value_objects.list import ListNameStr
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.message import messages


class TaskInterface(BaseInterface, group_name="task"):
    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        task_info = ctx.services.task_query.info(TaskAttributeSlotStr(task_name_or_alias), None if list_name is None else ListNameStr(list_name))

        data: dict[str, tuple[str, ...]] = {
            AttributeKind.ID.name.title(): (str(task_info.id),),
            AttributeKind.NAME.name.title(): (task_info.name.real.value,),
            AttributeKind.ALIAS.name.title(): tuple(alias.real.value for alias in task_info.aliases),
            **{
                attr.name.real.value: tuple(elem.real.value for elem in v) for attr, v in task_info.task_attribute_value_mapping.items()
            }
        }

        await messages.object_info(
            ctx.interaction, type(task_info), data
        )

class TasksInterface(BaseInterface, group_name="tasks"):
    pass
