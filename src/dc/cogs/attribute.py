import builtins
import enum
import itertools
import typing as t
from string.templatelib import Template
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
from structures.attribute.collection import Collection, CollectionEntry
from structures.attribute.slot_str import SLOT_TYPES
from utils import itertools2, text

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
    @command.adapt
    async def info(
        self,
        ia: InteractionAdapter,
        attribute: str,
        type: AnyAttributeEnum,
        list: str | None = None,
    ):
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        attr = list_obj.get_attribute(type.value, attribute)

        return ia.dc.response.send_message(
            message.layout(
                "Attribute Info",
                text.join_t(
                    "\n",
                    (
                        t"**{k:p}:** {v}"
                        for k, v in [
                            ("Name", attr.name),
                            ("Type", attr._o.__class__.type_name),
                            ("Slot Type", message.slot_type_to_name(attr.slot_type)),
                            ("Minimum Slot Count", attr.min_slots),
                            ("Maximum Slot Count", attr.max_slots),
                        ]
                    ),
                ),
                message_status=message.MessageStatus.INFO,
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt
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
    ) -> CoroutineType[None, None, t.Any]:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        attr = list_obj.create_attribute(
            type.value, name, slot_type.value, max_slots, aliases, collection
        )

        return ia.dc.response.send_message(
            layouts.success(
                f"{type.name} Created",
                t"The {type.name.lower()} {attr.name:,} has successfully been created!",
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt
    async def nuke(
        self,
        ia: InteractionAdapter,
        type: NonStaticAttributeEnum,
        attribute: str,
        list: str | None,
    ) -> CoroutineType[None, None, t.Any]:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        attr: AnyAttributeAdapterT = list_obj.get_attribute(type.value, attribute)

        return confirm.confirm_nuke(
            ia,
            attr._o,
            lambda: list_obj.delete_attribute(type.value, attr.name),
        )


def _collection_entry_to_browse_str(entry: CollectionEntry) -> str:
    if not entry.aliases:
        return f"({entry.value!r})"

    return f"({entry.value!r}: {' '.join(repr(alias) for alias in entry.aliases)})"


class AttributesCog(cmds.GroupCog, group_name="attributes"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt
    async def browse(
        self,
        ia: InteractionAdapter,
        type: AnyAttributeEnum | None = None,
        list: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        await ia.dc.response.defer()

        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        attr_to_aliases = {
            attr: tuple(item[0] for item in items)
            for attr, items in itertools2.groupby_unsorted(
                list_obj._o.get_attributes_by_alias(
                    ia._c, ..., type=None if type is None else type.value
                ).items(),
                lambda item: item[1],
            ).items()
        }

        attr_to_coll = {c.attribute: c for c in list_obj._o.get_collections(ia._c)}

        attrs = list_obj._o.get_attributes(ia._c, None if type is None else type.value)
        attrs.sort(key=lambda attr: attr.position)

        data: dict[str, tuple[str | tuple[str, ...], ...]] = {
            "Name": tuple(attr.name for attr in attrs),
            "Alias": tuple(attr_to_aliases.get(attr, ()) for attr in attrs),
            "Type": tuple(str(builtins.type(attr)).title() for attr in attrs),
            "Slot Type": tuple(
                message.slot_type_to_name(attr.slot_type) for attr in attrs
            ),
            "Position": tuple(str(attr.position) for attr in attrs),
            "Min Slots": tuple(str(attr.min_slots) for attr in attrs),
            "Max Slots": tuple(str(attr.max_slots) for attr in attrs),
            "Collection": tuple(
                tuple(map(_collection_entry_to_browse_str, attr_to_coll.get(attr, ())))
                for attr in attrs
            ),
        }

        return ia.dc.followup.send(
            await layouts.browse(
                BaseAttribute if type is None else type.value,
                tuple(zip(*data.values())),
                tuple(data),
            ),
            suppress_embeds=True,
        )
