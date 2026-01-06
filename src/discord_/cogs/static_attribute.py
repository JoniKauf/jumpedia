import enum
import typing as t
from string.templatelib import Template

import discord as dc
import discord.ext.commands as cmds
from discord import app_commands as acmds

from adapters.interaction import InteractionAdapter
from discord_.utils_ import shortcuts
from structures import list
from structures.attribute import (
    AnyAttributeT,
    StaticAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.attribute.slot_str import SLOT_TYPES
from structures.list import Kind, List
from utils import text

from ..utils_ import messaging, modal

SlotTypeEnum = enum.Enum(
    "SlotTypeEnum",
    [(messaging.slot_type_to_name(type), type) for type in SLOT_TYPES] + [],
)


async def info(
    interaction: dc.Interaction,
    type: type[AnyAttributeT],
    attribute: str,
    list: str | None = None,
) -> None:
    list_obj = shortcuts.get_specified_or_selected_or_default_list(
        InteractionAdapter(interaction), None, list
    )

    attr = list_obj.get_attribute(type, attribute)

    await interaction.response.send_message(
        messaging.layout(
            "Attribute Info",
            text.join_t(
                "\n",
                (
                    t"**{k:p}:** {v}"
                    for k, v in [
                        ("Name", attr.name),
                        ("Type", attr._s.__class__.type_name),
                        ("Slot Type", messaging.slot_type_to_name(attr.slot_type)),
                        ("Minimum Slot Count", attr.min_slots),
                        ("Maximum Slot Count", attr.max_slots),
                    ]
                ),
            ),
            message_status=messaging.MessageStatus.INFO,
        )
    )


async def browse(
    interaction: dc.Interaction, type: type[AnyAttributeT], list: str | None
) -> None:
    list_obj = shortcuts.get_specified_or_selected_or_default_list(
        InteractionAdapter(interaction), None, list
    )

    await interaction.response.send_message(
        messaging.layout(
            "All Attributes",
            Template(
                "\n".join(f"- {attr.name}" for attr in list_obj.get_attributes(type))
                or "None"
            ),
            messaging.MessageStatus.INFO,
        )
    )


async def create(
    interaction: dc.Interaction,
    type: type[TaskAttribute | UserAttribute],
    name: str,
    slot_type: SlotTypeEnum,
    max_slots: int,
    aliases: str | None,
    collection: str | None,
    list: str | None,
) -> None:
    list_obj = shortcuts.get_specified_or_selected_or_default_list(
        InteractionAdapter(interaction), None, list
    )

    attr = list_obj.create_attribute(
        type, name, slot_type.value, max_slots, aliases, collection
    )

    await interaction.response.send_message(
        messaging.layout(
            f"{type.type_name.title()} Created",
            t"The {type.type_name.lower()} {attr.name:p:c} has successfully been created!",
            messaging.MessageStatus.SUCCESS,
        )
    )


async def delete(
    interaction: dc.Interaction,
    type: type[TaskAttribute | UserAttribute],
    syn: str,
    list: str | None,
) -> None:
    list_obj = shortcuts.get_specified_or_selected_or_default_list(
        InteractionAdapter(interaction), None, list
    )

    attr_s = list_obj.get_attribute(type, syn)._s

    await modal.delete_structure_confirmation(
        interaction,
        type,
        attr_s.name,
        lambda _: list_obj._s.delete_attribute(type, attr_s.id),
    )


class StaticAttributeCog(cmds.GroupCog, group_name="static_attribute"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    if t.TYPE_CHECKING:
        StaticAttributesLiteral = str
    else:
        StaticAttributesLiteral = t.Literal[
            *(str(list.KIND_TO_PREDEFINED_DATA[kind].real_name) for kind in Kind)
        ]

    @acmds.command(description="Get information about a static attribute.")
    async def info(self, interaction: dc.Interaction, static_attribute: StaticAttributesLiteral, list: str | None = None) -> None:  # type: ignore
        await info(interaction, StaticAttribute, static_attribute, list)

    @acmds.command(description="Browse all static attributes.")
    async def browse(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> None:
        await browse(interaction, StaticAttribute, list)
