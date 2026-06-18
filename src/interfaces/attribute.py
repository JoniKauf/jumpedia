
from discord import app_commands

from domain.value_objects.attribute import AttributeSyn
from domain.value_objects.list import ListName
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.message import messages
from services.dtos.attribute import AttributeSummary


class AttributeInterface(BaseInterface, group_name="attribute"):
    @app_commands.command()
    @with_context()
    async def info(self, ctx: CommandContext, attribute_name: str, list_name: str | None = None) -> None:
        attr_info = ctx.services.attribute_query.info(AttributeSyn(attribute_name), None if list_name is None else ListName(list_name))

        data: dict[str, tuple[str, ...]] = {
            "Name": (attr_info.name.real.value,),
            "List": (attr_info.list.name.real.value,),
            "Type": (attr_info.type.name.title(),),
            "Kind": (attr_info.kind.name.title(),),
            "Slot Type": (attr_info.slot.type.name.title(),),
            "Minimum Slot Count": (str(attr_info.slot.min_count),),
            "Maximum Slot Count": (str(attr_info.slot.max_count),),
            "Position": (str(attr_info.position),)
        }

        await messages.object_info(ctx.interaction, type(attr_info), data)

    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext, list_name: str | None = None) -> None:
        summaries = ctx.services.attribute_query.summaries(None if list_name is None else ListName(list_name))

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            "Name": tuple((summary.name.real.value,) for summary in summaries),
            "List": tuple((summary.list.name.real.value,) for summary in summaries),
            "Type": tuple((summary.type.name.title(),) for summary in summaries),
            "Kind": tuple((summary.kind.name.title(),) for summary in summaries),
            "Slot Type": tuple((summary.slot.type.name.title(),) for summary in summaries),
            "Minimum Slot Count": tuple((str(summary.slot.min_count),) for summary in summaries),
            "Maximum Slot Count": tuple((str(summary.slot.max_count),) for summary in summaries),
            "Position": tuple((str(summary.position),) for summary in summaries),
        }

        await messages.object_browse(ctx.interaction, AttributeSummary, data)
