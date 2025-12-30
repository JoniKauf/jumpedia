import builtins
from string.templatelib import Template
from typing import Any

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters.interaction import InteractionAdapter
from discord_.utils_ import shortcuts
from structures.attribute import ALL_ATTRIBUTE_TYPES
from structures.list import List
from utils import text
from utils.rank import CommunityRank

from ..utils_ import messaging, modal, predicate


class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about a list.")
    async def info(self, interaction: dc.Interaction, list: str | None = None) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list((InteractionAdapter(interaction), None), list)

        info: builtins.list[tuple[str, Any]] = [("Name", list_obj.name)]

        attributes = list_obj.get_all_attributes()

        info.append(("Total Attribute Count", sum(len(type) for type in attributes)))

        for i, type in enumerate(attributes):
            info.append(
                (f"{ALL_ATTRIBUTE_TYPES[i].type_name.title()} Count", len(type))
            )

        info.append(("Task Count", len(list_obj.get_tasks())))

        await interaction.response.send_message(
            messaging.layout(
                "List Info",
                Template("\n".join(f"**{k}:** {v}" for k, v in info)),
                messaging.MessageStatus.INFO,
            )
        )

    @acmds.command(description="Browse all lists of the community.")
    async def browse(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        lists = shortcuts.get_current_community(InteractionAdapter(interaction)).get_lists()

        listing: Template

        if lists:
            listing = text.join_t("\n", (t"- {list.name}" for list in lists))
        else:
            listing = t"None"

        await interaction.response.send_message(
            messaging.layout(
                "All Lists",
                listing,
                messaging.MessageStatus.INFO,
            )
        )

    @acmds.command(description="Set the default selected list of the community.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def set_default_selected(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> None:
        community = shortcuts.get_current_community(InteractionAdapter(interaction))

        if list is not None:
            selected_list = community.get_list(list).name
        else:
            selected_list = None

        community.set_default_selected_list(selected_list)

        await interaction.response.send_message(
            messaging.layout(
                "Default Selected List Set",
                (
                    t"The default selected list has successfully been changed to `{list}`!"
                    if list is not None
                    else t"The default selected list has successfully been changed to be unset."
                ),
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Create a new list.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def create(self, interaction: dc.Interaction, list: str) -> None:
        community = shortcuts.get_current_community(InteractionAdapter(interaction))

        new_list = community.create_list(list)

        await interaction.response.send_message(
            messaging.layout(
                "List Created",
                t"The list `{new_list.name}` has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Delete an existing list.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def delete(self, interaction: dc.Interaction, list: str) -> None:
        list_s = shortcuts.get_current_community(InteractionAdapter(interaction)).get_list(list)._s

        await modal.delete_structure_confirmation(
            interaction,
            List,
            list_s.name,
            lambda _: list_s.community.delete_list(list_s.id),
        )
