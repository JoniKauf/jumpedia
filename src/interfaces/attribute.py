from string.templatelib import Template

from discord import app_commands

from domain.entities.attribute import AttributeEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeSlotType, AttributeType
from domain.sentinels.default import DEFAULT
from domain.typing.collection_entry import AbstractCollectionT
from domain.value_objects.attribute import AttributeFieldConfig, AttributeSynStr
from domain.value_objects.list import ListNameStr
from interfaces import bindings
from interfaces.base import BaseInterface
from interfaces.command import groups
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.enums.attribute import AttributeTypeInterfaceEnum
from interfaces.enums.edit_mode import (
    AliasEditModeInterfaceEnum,
    CollectionEditModeInterfaceEnum,
)
from interfaces.message.format import F
from interfaces.message import messages


def _collection_to_representation(
    collection: AbstractCollectionT,
) -> tuple[str, ...]:
    # Python's repr of strings aligns well with our string tokens, so we can just use that and it will be parsable again :)
    return tuple(
        f"({str(entry[0])!r}: {' '.join(repr(str(alias)) for alias in entry[1])})"
        for entry in collection
    )


class AttributeInterface(BaseInterface, group_name="attribute"):
    edit_group = groups.create_edit_group()

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
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        data: dict[str, tuple[str, ...]] = {
            "Name": (str(info.name),),
            "Alias": tuple(str(syn) for syn in info.aliases),
            "List": (str(info.list.name),),
            "Type": (info.type.name.title(),),
            "Kind": (info.kind.name.title(),),
            "Slot Type": (info.field_config.slot_type.name.title(),),
            "Minimum Slot Count": (str(info.field_config.min_slot_count),),
            "Maximum Slot Count": (str(info.field_config.max_slot_count),),
            "Unique Slots": ("True" if info.field_config.unique_slots else "False",),
            "Position": (str(info.position.value),),
            "Collection": _collection_to_representation(info.collection),
        }

        await messages.object_info(ctx.interaction, AttributeEntity, data)

    @app_commands.command()
    @with_context()
    async def create(
        self,
        ctx: CommandContext,
        attribute_name: str,
        list_name: str,
        type: AttributeTypeInterfaceEnum,
        slot_type: AttributeSlotType,
        max_slot_count: int,
        unique_slots: bool,
        aliases_dsl_sequence: str,
        collection_dsl_mapping: str,
    ) -> None:
        aliases = bindings.sequence.attribute_aliases(aliases_dsl_sequence)

        collection = bindings.mapping.collection(collection_dsl_mapping)

        attr = ctx.services.attribute.create(
            AttributeSynStr(attribute_name),
            ListNameStr(list_name),
            type.value,
            AttributeFieldConfig(slot_type, 0, max_slot_count, unique_slots),
            aliases,
            collection,
        )

        await messages.object_created(ctx.interaction, attr)

    @app_commands.command()
    @with_context()
    async def nuke(
        self, ctx: CommandContext, attribute_name: str, list_name: str
    ) -> None:
        prepared, lst, attr = ctx.services.attribute_prepare.delete(
            AttributeSynStr(attribute_name), ListNameStr(list_name)
        )

        consequences: Template = (
            t"Each field of every {F.type_name(TaskEntity)} for this specific {F.type_name(AttributeEntity)} will be deleted!"
            if attr.type is AttributeType.TASK
            else t"Each custom field of every {F.type_name(MemberEntity)} who has given themselves this {F.type_name(TaskEntity)} will be deleted!"
        )

        await messages.nuke_object_on_confirmation(
            ctx.interaction,
            to_nuke=attr,
            parent=lst,
            consequences=consequences,
            execute=lambda: ctx.services.attribute.delete(prepared),
        )

    @edit_group.command(name="name")
    @with_context()
    async def edit_name(
        self,
        ctx: CommandContext,
        attribute_name: str,
        list_name: str,
        new_attribute_name: str,
    ) -> None:
        after = AttributeSynStr(new_attribute_name)
        before = ctx.services.attribute.edit_name(
            AttributeSynStr(attribute_name), after, ListNameStr(list_name)
        )

        await messages.object_name_edited(
            ctx.interaction, AttributeEntity, before, after
        )

    @edit_group.command(name="aliases")
    @with_context()
    async def edit_aliases(
        self,
        ctx: CommandContext,
        attribute_name: str,
        list_name: str,
        new_attribute_aliases_dsl_sequence: str,
        edit_mode: AliasEditModeInterfaceEnum,
    ) -> None:
        after = bindings.sequence.attribute_aliases(new_attribute_aliases_dsl_sequence)
        attr = ctx.services.attribute.edit_aliases(
            AttributeSynStr(attribute_name),
            after,
            ListNameStr(list_name),
            edit_mode.value,
        )

        await messages.object_aliases_edited(ctx.interaction, attr)

    @edit_group.command(name="min_and_max_slot_count")
    @with_context()
    async def edit_min_and_max_slot_count(
        self,
        ctx: CommandContext,
        attribute_name: str,
        list_name: str,
        new_min_slot_count: int,
        new_max_slot_count: int,
    ) -> None:
        attr = ctx.services.attribute.edit_min_and_max_slot_count(
            AttributeSynStr(attribute_name),
            ListNameStr(list_name),
            new_min_slot_count,
            new_max_slot_count,
        )

        await messages.success(
            ctx.interaction,
            t"{F.type_name(AttributeEntity)} Min And Max Slot Count Edited",
            t"The min and max slot count for the {F.mention(attr)} has been set to "
            + t"{F.raw(str(attr.field_config.min_slot_count))} and {F.raw(str(attr.field_config.max_slot_count))} successfully!"
            + (
                t""
                if attr.type is AttributeType.TASK
                else t"\n\nUsers' field data for this {F.type_name(AttributeEntity)} was not validated and may therefore still exceed the new bounds. Manually edit their data if deemed necessary!"
            ),
        )

    @edit_group.command(name="collection")
    @with_context()
    async def edit_collection(
        self,
        ctx: CommandContext,
        attribute_name: str,
        list_name: ListNameStr,
        new_collection_dsl_mapping: str,
        edit_mode: CollectionEditModeInterfaceEnum,
    ) -> None:
        new_collection = bindings.mapping.collection(new_collection_dsl_mapping)

        attr = ctx.services.attribute.edit_collection(
            AttributeSynStr(attribute_name), list_name, new_collection, edit_mode.value
        )

        await messages.success(
            ctx.interaction,
            t"{F.type_name(AttributeEntity)} Collection Edited",
            t"The collection for the {F.mention(attr)} has been edited successfully!"
            + (
                t""
                if attr.type is AttributeType.TASK
                else t"\n\nUsers' field data for this {F.type_name(AttributeEntity)} was not validated and may therefore be invalid for the new collection. Manually edit their data if deemed necessary!"
            ),
        )


class AttributesInterface(BaseInterface, group_name="attributes"):
    edit_group = groups.create_edit_group()

    @app_commands.command()
    @with_context()
    async def browse(self, ctx: CommandContext, list_name: str | None = None) -> None:
        summaries = ctx.services.attribute_query.get_summaries(
            DEFAULT if list_name is None else ListNameStr(list_name)
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
                (summary.field_config.slot_type.name.title(),) for summary in summaries
            ),
            "Minimum Slot Count": tuple(
                (str(summary.field_config.min_slot_count),) for summary in summaries
            ),
            "Maximum Slot Count": tuple(
                (str(summary.field_config.max_slot_count),) for summary in summaries
            ),
            "Unique Slots": tuple(
                ("True" if summary.field_config.unique_slots else "False",)
                for summary in summaries
            ),
            "Position": tuple((str(summary.position.value),) for summary in summaries),
            "Collection": tuple(
                _collection_to_representation(summary.collection)
                for summary in summaries
            ),
        }

        await messages.object_browse(ctx.interaction, AttributeEntity, data)

    @edit_group.command(name="position_order")
    @with_context()
    async def edit_position_order(
        self, ctx: CommandContext, all_attribute_names_dsl_sequence: str, list_name: str
    ) -> None:
        lst = ctx.services.attribute.edit_position_order(
            bindings.sequence.attributes(all_attribute_names_dsl_sequence),
            ListNameStr(list_name),
        )

        await messages.success(
            ctx.interaction,
            t"{F.type_name(AttributeEntity, plural=True)} Position Order Edited",
            t"The positions and therefore the ordering of all {F.type_name(AttributeEntity, plural=True)} of the {F.mention(lst)} has been edited successfully!",
        )
