import enum

from discord import app_commands

from domain.enums.attribute import AttributeSlotType, AttributeType
from domain.value_objects.attribute import AttributeSlot, AttributeSyn
from domain.value_objects.attribute_collection_entry import AttributeCollectionEntrySyn
from domain.value_objects.list import ListName
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.dsl.value_list.interpreter import ValueListInterpreter
from interfaces.dsl.value_to_value_list_mapping.interpreter import (
    ValueToValueListInterpreter,
)
from interfaces.message import messages
from services.dtos.attribute_collection_entry import CreateAttributeCollectionEntry
from services.dtos.attribute import AttributeSummary


class AttributeInterface(BaseInterface, group_name="attribute"):
    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, attribute_name: str, list_name: str | None = None
    ) -> None:
        attr_info = ctx.services.attribute_query.info(
            AttributeSyn(attribute_name),
            None if list_name is None else ListName(list_name),
        )

        data: dict[str, tuple[str, ...]] = {
            "Name": (attr_info.name.real.value,),
            "List": (attr_info.list.name.real.value,),
            "Type": (attr_info.type.name.title(),),
            "Kind": (attr_info.kind.name.title(),),
            "Slot Type": (attr_info.slot.type.name.title(),),
            "Minimum Slot Count": (str(attr_info.slot.min_count),),
            "Maximum Slot Count": (str(attr_info.slot.max_count),),
            "Position": (str(attr_info.position),),
        }

        await messages.object_info(ctx.interaction, type(attr_info), data)

    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext, list_name: str | None = None) -> None:
        summaries = ctx.services.attribute_query.summaries(
            None if list_name is None else ListName(list_name)
        )

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            "Name": tuple((summary.name.real.value,) for summary in summaries),
            "List": tuple((summary.list.name.real.value,) for summary in summaries),
            "Type": tuple((summary.type.name.title(),) for summary in summaries),
            "Kind": tuple((summary.kind.name.title(),) for summary in summaries),
            "Slot Type": tuple(
                (summary.slot.type.name.title(),) for summary in summaries
            ),
            "Minimum Slot Count": tuple(
                (str(summary.slot.min_count),) for summary in summaries
            ),
            "Maximum Slot Count": tuple(
                (str(summary.slot.max_count),) for summary in summaries
            ),
            "Position": tuple((str(summary.position),) for summary in summaries),
        }

        await messages.object_browse(ctx.interaction, AttributeSummary, data)

    class NonStaticAttributeTypesEnum(enum.Enum):
        TASK = AttributeType.TASK
        USER = AttributeType.USER

    @app_commands.command()
    @with_context()
    async def create(
        self,
        ctx: CommandContext,
        attribute_name: str,
        list_name: str,
        type: NonStaticAttributeTypesEnum,
        slot_type: AttributeSlotType,
        max_slot_count: int,
        aliases_dsl: str | None = None,
        collection_dsl: str | None = None,
    ) -> None:
        ctx.services.attribute.create(
            AttributeSyn(attribute_name),
            type.value,
            AttributeSlot(slot_type, 0, max_slot_count),
            (
                ()
                if aliases_dsl is None
                else tuple(
                    map(AttributeSyn, ValueListInterpreter().interpret(aliases_dsl))
                )
            ),
            (
                ()
                if collection_dsl is None
                else tuple(
                    CreateAttributeCollectionEntry(
                        AttributeCollectionEntrySyn(k),
                        tuple(AttributeCollectionEntrySyn(elem) for elem in v),
                    )
                    for k, v in ValueToValueListInterpreter().interpret(collection_dsl)
                )
            ),
            ListName(list_name),
        )
