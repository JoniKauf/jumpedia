import enum
import itertools
import typing as t
from string.templatelib import Template
from types import CoroutineType

import discord.ext.commands as cmds
from discord import app_commands as acmds

from adapting._attribute import AnyAttributeAdapterT
from adapting.interaction import InteractionAdapter
from dc_utils import command, confirm, message, modal, predicate, shortcuts
from dc_utils.rank import CommunityRank
from structures.attribute import ALL_ATTRIBUTE_TYPES, TaskAttribute, UserAttribute
from structures.attribute.slot_str import SLOT_TYPES
from utils import text

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
            message.layout(
                f"{type.name} Created",
                t"The {type.name.lower()} {attr.name:,} has successfully been created!",
                message.MessageStatus.SUCCESS,
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
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        return ia.dc.response.send_message(
            message.layout(
                "All Attributes",
                Template(
                    "\n".join(
                        f"- {attr}"
                        for attr in (
                            itertools.chain.from_iterable(list_obj.get_all_attributes())
                            if type is None
                            else list_obj.get_attributes(type.value)
                        )
                    )
                    or "None"
                ),
                message.MessageStatus.INFO,
            )
        )
