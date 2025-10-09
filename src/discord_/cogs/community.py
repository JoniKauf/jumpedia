from enum import Enum

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from ... import ranks
from ...adapters.interaction import InteractionAdapter
from ..structs import modals, predicates, views
from ..utils import messaging
from ...ranks.community_rank import CommunityRank
from ...ranks.server_rank import ServerRank


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about the community.")
    async def info(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)
        community = ia.jumpedia.get_current_community()

        default_selected_list = community.get_default_selected_list()
        default_selected_list_name = (
            default_selected_list.name if default_selected_list is not None else "None"
        )

        await interaction.response.send_message(
            messaging.layout(
                "Community Info",
                "\n".join(
                    f"**{k}:** {v}"
                    for k, v in [
                        ("Name", community.name),
                        ("Server Count", community.get_server_count()),
                        ("List Count", len(community.get_lists())),
                        ("Default Selected List", default_selected_list_name),
                    ]
                ),
                messaging.MessageStatus.INFO,
            )
        )

    get_group = acmds.Group(name="get", description="Get objects of the community.")

    @get_group.command(name="lists", description="Get all lists of the community.")
    async def get_lists(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        community = ia.jumpedia.get_current_community()

        await interaction.response.send_message(
            messaging.layout(
                "All Lists",
                ",".join(f"- {list.name}" for list in community.get_lists()) or "None",
                messaging.MessageStatus.INFO,
            )
        )

    set_group = acmds.Group(
        name="set", description="Set values for objects of the community."
    )

    @set_group.command(
        name="default_selected_list",
        description="Set the default selected list of the community.",
    )
    @acmds.check(predicates.rank_required(ServerRank.SERVER_ADMINISTRATOR))
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
                    f"The default selected list has successfully been changed to `{list}`!"
                    if list is not None
                    else "The default selected list has successfully been changed to be unset, meaning that users are forced to select one."
                ),
                messaging.MessageStatus.SUCCESS,
            )
        )

    create_group = acmds.Group(
        name="create", description="Create new objects for the community."
    )

    @create_group.command(name="list", description="Create a new list.")
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def create_list(self, interaction: dc.Interaction, list_name: str) -> None:
        ia = InteractionAdapter(interaction)

        new_list = ia.jumpedia.get_current_community().create_list(list_name)

        await interaction.response.send_message(
            messaging.layout(
                "List Created",
                f"The list `{new_list.name}` has been created successfully!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    delete_group = acmds.Group(
        name="delete", description="Delete objects from the community."
    )

    @delete_group.command(
        name="delete", description="Delete a list from the community."
    )
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def delete_list(self, interaction: dc.Interaction, list_name: str) -> None:
        ia = InteractionAdapter(interaction)

        list = ia.jumpedia.get_current_community().get_list(list_name)

        async def after_submit(interaction: dc.Interaction, success: bool) -> None:
            if success:
                ctx.community.delete_list(list_name)

                return await interaction.response.send_message(
                    messaging.layout(
                        "List Deleted",
                        f"The list `{list.name}` has successfully been deleted!",
                        messaging.MessageStatus.SUCCESS,
                    )
                )

            await interaction.response.send_message(
                messaging.layout(
                    "List Deletion Aborted",
                    f"The list `{list.name}` has **not** been deleted because the name entered is not correct!",
                    messaging.MessageStatus.WARNING,
                )
            )

        await interaction.response.send_modal(
            modals.ConfirmByEnteringModal(
                interaction,
                "Confirm List Deletion",
                "Re-Enter the list's name to confirm",
                lambda s: s == list.name,
                after_submit,
            )
        )
