import enum

from discord import app_commands

from domain.enums.attribute import AttributeSlotType, AttributeType
from domain.value_objects.attribute import AttributeSlot, AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.list import ListNameStr
from interfaces import dsl
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.message import format, messages
from services.dtos.attribute import AttributeSummary
from services.dtos.collection_entry import (
    CollectionEntryEntityWithAliases,
    CreateCollectionEntry,
)


def _collection_to_representation(
    collection: tuple[CollectionEntryEntityWithAliases, ...],
) -> tuple[str, ...]:
    # Python's repr of strings aligns well with our string tokens.
    return tuple(
        f"({str(item.entry.value)!r}: {' '.join(repr(str(alias)) for alias in item.aliases)})"
        for item in collection
    )


class AttributeInterface(BaseInterface, group_name="attribute"):
    @app_commands.command()
    @with_context()
    async def info(
        self,
        ctx: CommandContext,
        attribute_name_or_alias: str,
        list_name: str | None = None,
    ) -> None:
        info = ctx.services.attribute_query.get_info(
            AttributeSynStr(attribute_name_or_alias),
            None if list_name is None else ListNameStr(list_name),
        )

        data: dict[str, tuple[str, ...]] = {
            "Name": (str(info.name),),
            "Alias": tuple(str(syn) for syn in info.aliases),
            "List": (str(info.list.name),),
            "Type": (info.type.name.title(),),
            "Kind": (info.kind.name.title(),),
            "Slot Type": (info.slot.type.name.title(),),
            "Minimum Slot Count": (str(info.slot.min_count),),
            "Maximum Slot Count": (str(info.slot.max_count),),
            "Position": (str(info.position.value),),
            "Collection": _collection_to_representation(info.collection),
        }

        await messages.object_info(ctx.interaction, type(info), data)

    NonStaticAttributeTypesEnum = enum.Enum(
        "NonStaticAttributeTypesEnum",
        [
            (format.ATTRIBUTE_TYPE_PREFIX_MAP[attr_type].title(), attr_type)
            for attr_type in AttributeType
            if attr_type is not AttributeType.STATIC
        ]
        + [],  # Pyright is happy with this enum inside a type annotation only if we add a "+ []"
    )

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
        aliases: tuple[AttributeSynStr, ...] = ()

        if aliases_dsl is not None:
            aliases = tuple(map(AttributeSynStr, (aliases_dsl)))

        collection: tuple[CreateCollectionEntry, ...] = ()

        if collection_dsl:
            collection = tuple(
                CreateCollectionEntry(
                    FieldSlotStr(k),
                    tuple(FieldSlotStr(elem) for elem in v),
                )
                for k, v in dsl.value_list.engine.eval(collection_dsl)
            )

        attr = ctx.services.attribute.create(
            AttributeSynStr(attribute_name),
            ListNameStr(list_name),
            type.value,
            AttributeSlot(slot_type, 0, max_slot_count),
            aliases,
            collection,
        )

        await messages.object_created(ctx.interaction, attr)

    @app_commands.command()
    @with_context()
    async def nuke(
        self, ctx: CommandContext, attribute_name: str, list_name: str
    ) -> None:
        deleted = ctx.services.attribute.delete(
            AttributeSynStr(attribute_name), ListNameStr(list_name)
        )

        await messages.object_nuked(ctx.interaction, deleted)

    @app_commands.command()
    @with_context()
    async def edit_name(
        self,
        ctx: CommandContext,
        current_attribute_name: str,
        new_attribute_name: str,
        list_name: str,
    ) -> None:
        attr = ctx.services.attribute.edit_name(AttributeSynStr(current_attribute_name), AttributeSynStr(new_attribute_name), ListNameStr(list_name))

        # TODO Make old name be correctly cased
        await messages.object_name_edited(ctx.interaction, )

class AttributesInterface(BaseInterface, group_name="attributes"):
    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext, list_name: str | None = None) -> None:
        summaries = ctx.services.attribute_query.get_summaries(
            None if list_name is None else ListNameStr(list_name)
        )

        data: dict[str, tuple[tuple[str, ...], ...]] = {
            "Name": tuple((str(summary.name),) for summary in summaries),
            "Alias": tuple(
                tuple(str(syn) for syn in summary.aliases) for summary in summaries
            ),
            "List": tuple((str(summary.list.name),) for summary in summaries),
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
            "Position": tuple((str(summary.position.value),) for summary in summaries),
            "Collection": tuple(
                _collection_to_representation(summary.collection)
                for summary in summaries
            ),
        }

        await messages.object_browse(ctx.interaction, AttributeSummary, data)
