import builtins
import enum
import typing as t
from types import CoroutineType

import discord.ext.commands as cmds
from discord import app_commands as acmds

from adapting._attribute import AnyAttributeAdapterT
from adapting.interaction import InteractionAdapter
from dc_utils import command, confirm, layouts, message, predicate, shortcuts
from dc_utils.rank import CommunityRank
from structures.attribute import (
    ALL_ATTRIBUTE_TYPES,
    BaseAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.attribute.collection import CollectionEntry
from structures.attribute.slot_str import SLOT_TYPES
from utils import itertools2


def _collection_entry_to_browse_str(entry: CollectionEntry) -> str:
    if not entry.aliases:
        return f"({entry.value!r})"

    return f"({entry.value!r}: {' '.join(repr(alias) for alias in entry.aliases)})"


class _AttrRow(t.NamedTuple):
    name: str
    alias: tuple[str, ...]
    type: str
    slot_type: str
    position: str
    min_slots: str
    max_slots: str
    collection: tuple[str, ...]


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
        ia: InteractionAdapter,
        attribute: str,
        list: str | None = None,
    ) -> CoroutineType:
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
                str(attr.min_slots),
                str(attr.max_slots),
                tuple(map(_collection_entry_to_browse_str, attr.get_collection(ia._c))),
            ),
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt()
    async def create(
        self,
        ia: InteractionAdapter,
        type: NonStaticAttributeEnum,
        name: str,
        slot_type: SlotTypeEnum,
        max_slots: int,
        aliases: str | None,
        collection: str | None,
        list: str | None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        attr = list_obj.create_attribute(
            type.value, name, slot_type.value, max_slots, aliases, collection
        )

        return ia.dc.followup.send(
            layouts.success(
                f"{type.name} Created",
                t"The {type.name.lower()} {attr.name:,} has successfully been created!",
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt()
    async def nuke(
        self,
        ia: InteractionAdapter,
        type: NonStaticAttributeEnum,
        attribute: str,
        list: str,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        attr: AnyAttributeAdapterT = list_obj.get_attribute(type.value, attribute)

        return confirm.confirm_nuke(
            ia,
            attr._o,
            lambda: list_obj.delete_attribute(type.value, attr.name),
        )

    attribute_edit_group = acmds.Group(name="edit", description="Edit attribute data.")

    @attribute_edit_group.command(name="name")
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    @command.adapt()
    async def edit_name(
        self,
        ia: InteractionAdapter,
        type: AnyAttributeEnum,
        attribute: str,
        new_name: str,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_attr, new_name = list_obj.edit_attribute_name(
            type.value, attribute, new_name
        )

        return ia.dc.followup.send(
            layouts.success(
                "Attribute Name Edited",
                t"The name of the "
                + old_attr.mention()
                + t" has successfully been changed to {new_name:,}!",
            )
        )


class AttributesCog(cmds.GroupCog, group_name="attributes"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt()
    async def browse(
        self,
        ia: InteractionAdapter,
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
                    str(attr.min_slots),
                    str(attr.max_slots),
                    tuple(
                        map(_collection_entry_to_browse_str, attr_to_coll.get(attr, ()))
                    ),
                )
                for attr in attrs
            ),
        )
