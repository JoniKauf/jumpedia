from string.templatelib import Template

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters.interaction import InteractionAdapter
from discord_.utils_ import group
from structures.community import Community
from structures.list import List
from utils import text
from utils.rank import CommunityRank, ServerRank

# from ..utils_ import messaging, modal, predicate


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about the community.")
    async def info(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)
        community = ia.jumpedia.get_current_community()

        default_selected_list = community.get_default_selected_list(None)
        default_selected_list_name = (
            default_selected_list.name if default_selected_list is not None else "None"
        )

        await interaction.response.send_message(
            messaging.layout(
                "Community Info",
                text.join_t(
                    "\n",
                    (
                        t"**{k:p}:** {v}"
                        for k, v in [
                            ("Name", community.name),
                            ("Server Count", community.get_server_count()),
                            ("List Count", len(community.get_lists())),
                            ("Default Selected List", default_selected_list_name),
                        ]
                    ),
                ),
                messaging.MessageStatus.INFO,
            )
        )

    get_group = group.get_get_group(Community)

    @get_group.command(name="lists", description="Get all lists of the community.")
    async def get_lists(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        lists = ia.jumpedia.get_current_community().get_lists()

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

    @get_group.command(
        name="default_selected_list",
        description="Get the default selected list of the commuity.",
    )
    async def get_default_selected_list(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        dsl = ia.jumpedia.get_current_community().get_default_selected_list(None)

        await interaction.response.send_message(
            messaging.layout(
                "Default Selected List",
                (
                    t"No list is set as the default selected list!"
                    if dsl is None
                    else t"The current default selected list of this community is `{dsl.name:p}`!"
                ),
                messaging.MessageStatus.INFO,
            )
        )

    set_group = group.get_set_group(Community)

    @set_group.command(
        name="default_selected_list",
        description="Set the default selected list of the community.",
    )
    @acmds.check(predicate.rank_required(ServerRank.ADMINISTRATOR))
    async def set_default_selected_list(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> None:
        ia = InteractionAdapter(interaction)
        community = ia.jumpedia.get_current_community()

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
                    else t"The default selected list has successfully been changed to be unset, meaning that users are forced to select one."
                ),
                messaging.MessageStatus.SUCCESS,
            )
        )

    create_group = group.get_create_group(Community)

    @create_group.command(name="list", description="Create a new list.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def create_list(self, interaction: dc.Interaction, list: str) -> None:
        ia = InteractionAdapter(interaction)
        new_list = ia.jumpedia.get_current_community().create_list(list)

        await interaction.response.send_message(
            messaging.layout(
                "List Created",
                t"The list `{new_list.name}` has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    delete_group = group.get_delete_group(Community)

    @delete_group.command(name="list", description="Delete a list from the community.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def delete_list(self, interaction: dc.Interaction, list: str) -> None:
        ia = InteractionAdapter(interaction)

        list_s = ia.jumpedia.get_current_community().get_list(list)._s

        await modal.delete_structure_confirmation(
            interaction,
            List,
            list_s.name,
            lambda _: list_s.community.delete_list(list_s.id),
        )
