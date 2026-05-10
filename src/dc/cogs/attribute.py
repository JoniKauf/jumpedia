import builtins
import enum
import typing as t
from types import CoroutineType

import discord.ext.commands as cmds
from discord import app_commands as acmds

from _adapters._attribute import AnyAttributeAdapterT
from _adapters.interaction import _InteractionAdapter
from dc_utils import command, confirm, group, layouts, message, predicate, shortcuts
from structures.attribute import (
    ALL_ATTRIBUTE_TYPES,
    BaseAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.attribute.collection import CollectionEntry
from structures.attribute.slot_str import SLOT_TYPES
from utils import itertools2
from domain.enum.rank import CommunityRank


def _collection_entry_to_browse_str(entry: CollectionEntry) -> str:
    if not entry.aliases:
        return f"({entry.value!r})"

    return f"({entry.value!r}: {' '.join(repr(alias) for alias in entry.aliases)})"


_AttrRow = command.row_type_factory[
    str, tuple[str, ...], str, str, str, str, str, tuple[str, ...]
](
    "Name",
    "Alias",
    "Type",
    "Slot Type",
    "Position",
    "Min Slot Count",
    "Max Slot Count",
    "Collection",
)


SlotTypeEnum = enum.Enum(
    "SlotTypeEnum",
    [(message.slot_type_to_name(type), type) for type in SLOT_TYPES] + [],
)

AnyAttributeEnum = enum.Enum(
    "AnyAttributeEnum",
    [(type.type_name.title(), type) for type in ALL_ATTRIBUTE_TYPES] + [],
)

NonStaticAttributeEnum = enum.Enum(
    "NonStaticAttributeEnum",
    [(type.type_name.title(), type) for type in (TaskAttribute, UserAttribute)] + [],
)


class AttributeCog(cmds.GroupCog, group_name="attribute"):
    @acmds.command()
    @command.adapt()
    async def info(
        self,
        ia: _InteractionAdapter,
        attribute: str,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        attr = (
            shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)
            .get_attribute(..., attribute)
            ._o
        )

        del list, attribute

        return await command.info(
            ia,
            attr,
            _AttrRow(
                attr.name,
                tuple(attr.get_aliases(ia._c)),
                str(type(attr)).title(),
                message.slot_type_to_name(attr.slot_type),
                str(attr.position),
                str(attr.min_slot_count),
                str(attr.max_slot_count),
                tuple(map(_collection_entry_to_browse_str, attr.get_collection(ia._c))),
            ),
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt()
    async def create(
        self,
        ia: _InteractionAdapter,
        list: str,
        type: NonStaticAttributeEnum,
        name: str,
        slot_type: SlotTypeEnum,
        max_slot_count: int,
        aliases: str | None = None,
        collection: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        attr = list_obj.create_attribute(
            type.value, name, slot_type.value, max_slot_count, aliases, collection
        )

        return ia.dc.followup.send(layouts.structure_created(attr._o))

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt()
    async def nuke(
        self,
        ia: _InteractionAdapter,
        list: str,
        type: NonStaticAttributeEnum,
        attribute: str,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        attr: AnyAttributeAdapterT = list_obj.get_attribute(type.value, attribute)

        return await confirm.confirm_nuke(
            ia,
            attr._o,
            lambda: list_obj.delete_attribute(type.value, attr.name),
        )

    attribute_edit_group = group.create_edit_group(
        min_required_rank=CommunityRank.ADMINISTRATOR
    )

    @attribute_edit_group.command(name="name")
    @command.adapt()
    async def edit_name(
        self,
        ia: _InteractionAdapter,
        list: str,
        type: AnyAttributeEnum,
        attribute: str,
        new_name: str,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_attr, new_name = list_obj.edit_attribute_name(
            type.value, attribute, new_name
        )

        return ia.dc.followup.send(layouts.structure_name_edited(old_attr._o, new_name))

    @attribute_edit_group.command(name="aliases")
    @command.adapt()
    async def edit_aliases(
        self,
        ia: _InteractionAdapter,
        list: str,
        type: AnyAttributeEnum,
        attribute: str,
        new_aliases: str,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_attr, aliases = list_obj.edit_attribute_aliases(
            type.value, attribute, new_aliases
        )

        return ia.dc.followup.send(
            layouts.structure_aliases_edited(old_attr._o, aliases)
        )

    @attribute_edit_group.command(name="min_and_max_slot_count")
    @command.adapt()
    async def edit_min_and_max_slot_count(
        self,
        ia: _InteractionAdapter,
        list: str,
        type: NonStaticAttributeEnum,
        attribute: str,
        new_min_slot_count: int,
        new_max_slot_count: int,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_attr = list_obj.edit_attribute_min_and_max_slot_count(
            type.value, attribute, new_min_slot_count, new_max_slot_count
        )

        return ia.dc.followup.send(
            layouts.success(
                f"{builtins.type(old_attr._o).type_name.title()} Min And Max Slot Count Edited",
                t"The min and max slot count of the "
                + layouts.mention(old_attr._o)
                + t" have been changed to {new_min_slot_count:,} and {new_max_slot_count:,} successfully!",
            )
        )


class AttributesCog(cmds.GroupCog, group_name="attributes"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt()
    async def browse(
        self,
        ia: _InteractionAdapter,
        type: AnyAttributeEnum | None = None,
        list: str | None = None,
    ) -> CoroutineType:
        attr_type = ... if type is None else type.value

        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)
        list_s = list_obj._o
        del list

        attr_to_aliases = {
            attr: tuple(item[0] for item in items)
            for attr, items in itertools2.groupby_unsorted(
                list_s.get_attributes_by_alias(ia._c, ..., type=attr_type).items(),
                lambda item: item[1],
            ).items()
        }

        attr_to_coll = {c.attribute: c for c in list_s.get_collections(ia._c)}

        attrs = list_s.get_attributes(ia._c, type=attr_type)
        attrs.sort(key=lambda attr: attr.position)

        return await command.browse(
            ia,
            BaseAttribute if attr_type is ... else attr_type,
            tuple(
                _AttrRow(
                    attr.name,
                    attr_to_aliases.get(attr, ()),
                    str(builtins.type(attr)).title(),
                    message.slot_type_to_name(attr.slot_type),
                    str(attr.position),
                    str(attr.min_slot_count),
                    str(attr.max_slot_count),
                    tuple(
                        map(_collection_entry_to_browse_str, attr_to_coll.get(attr, ()))
                    ),
                )
                for attr in attrs
            ),
        )
