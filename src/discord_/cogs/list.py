import builtins
from string.templatelib import Template
from typing import Any

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters.interaction import InteractionAdapter
from discord_.utils_ import command, shortcuts
from structures.attribute import ALL_ATTRIBUTE_TYPES
from structures.list import List
from utils import text
from utils.rank import CommunityRank

from ..utils_ import message, modal, predicate


class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about a list.")
    @command.adapt
    async def info(self, ia: InteractionAdapter, list: str | None = None) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        info: builtins.list[tuple[str, Any]] = [("Name", list_obj.name)]

        attributes = list_obj.get_all_attributes()

        info.append(("Total Attribute Count", sum(len(type) for type in attributes)))

        for i, type in enumerate(attributes):
            info.append(
                (f"{ALL_ATTRIBUTE_TYPES[i].type_name.title()} Count", len(type))
            )

        info.append(("Task Count", len(list_obj.get_tasks())))

        await ia.dc.response.send_message(
            message.layout(
                "List Info",
                Template("\n".join(f"**{k}:** {v}" for k, v in info)),
                message.MessageStatus.INFO,
            )
        )

    @acmds.command(description="Browse all lists of the community.")
    @command.adapt
    async def browse(self, ia: InteractionAdapter) -> None:
        lists = shortcuts.get_current_community(ia).get_lists()

        listing: Template

        if lists:
            listing = text.join_t("\n", (t"- {list.name}" for list in lists))
        else:
            listing = t"None"

        await ia.dc.response.send_message(
            message.layout(
                "All Lists",
                listing,
                message.MessageStatus.INFO,
            )
        )

    @acmds.command(description="Create a new list.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt
    async def create(self, ia: InteractionAdapter, list: str) -> None:
        community = shortcuts.get_current_community(ia)

        new_list = community.create_list(list)

        await ia.dc.response.send_message(
            message.layout(
                "List Created",
                t"The list {new_list.name:,} has successfully been created!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Delete an existing list.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt
    async def nuke(self, ia: InteractionAdapter, list: str) -> None:
        list_s = shortcuts.get_current_community(ia).get_list(list)._o

        await modal.delete_structure_confirmation(
            ia.dc,
            List,
            list_s.name,
            lambda _: list_s.community.delete_list(ia._c, list_s.id),
        )
