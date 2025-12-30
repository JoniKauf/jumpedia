from string.templatelib import Template

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._user import UserAdapter
from adapters.interaction import InteractionAdapter
from discord_.utils_ import shortcuts
from structures.community import Community
from utils import text
from utils.rank import CommunityRank, JumpediaRank, ServerRank

from ..utils_ import messaging, modal, predicate


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about the community.")
    async def info(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)
        community = shortcuts.get_current_community(ia)

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

    @acmds.command(description="Browse all communities.")
    async def browse(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        communities = ia.jumpedia.get_communities()

        listing: Template

        if communities:
            listing = text.join_t("\n", (t"- {comm.name:p}" for comm in communities))
        else:
            listing = t"None"

        await interaction.response.send_message(
            messaging.layout(
                "All Communities",
                listing,
                messaging.MessageStatus.INFO,
            )
        )

    @acmds.command(description="Create a community.")
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    async def create(
        self,
        interaction: dc.Interaction,
        community_name: str,
        initial_list_name: str | None = None,
    ) -> None:
        jumpedia = InteractionAdapter(interaction).jumpedia

        community = jumpedia.create_community(community_name, initial_list_name)

        await interaction.response.send_message(
            messaging.layout(
                "Community Created",
                t"The community `{community.name:p}` was successfully created and is now connected to this server!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Delete a community.")
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    async def delete(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)
        community = shortcuts.get_current_community(ia)

        await modal.delete_structure_confirmation(
            ia._s,
            Community,
            community._s.name,
            lambda _: ia.jumpedia.delete_community(community.name),
        )

    @acmds.command(description="Connect a community to this server.")
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    async def connect(self, interaction: dc.Interaction, community_name: str) -> None:
        ia = InteractionAdapter(interaction)

        community = ia.jumpedia.add_community_to_current_server(community_name)

        await interaction.response.send_message(
            messaging.layout(
                "Community Connected",
                t"This server has successfully been connected to the community `{community.name:p}`!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Disconnect a community from this server.")
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    async def disconnect(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        community = ia.jumpedia.remove_community_from_current_server()

        await interaction.response.send_message(
            messaging.layout(
                "Community Disconnected",
                t"The community `{community.name:p}` has successfully been disconnected from this server!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Transfer the ownership of a community to another user.")
    @acmds.check(predicate.rank_required(CommunityRank.OWNER))
    async def transfer_ownership(
        self, interaction: dc.Interaction, user: dc.User
    ) -> None:
        community = shortcuts.get_current_community(InteractionAdapter(interaction))
        transfer_jumpedia_user = shortcuts.get_or_create_specified_or_current_jumpedia_user(community.jumpedia, user)

        async def after_submit(interaction: dc.Interaction, success: bool) -> None:
            if success:
                current_community_user = (
                    shortcuts.get_or_create_specified_or_current_community_user(community, None)
                )

                community.get_or_create_community_user(
                    transfer_jumpedia_user
                ).transfer_ownership(current_community_user)

                await interaction.response.send_message(
                    messaging.layout(
                        f"Ownership Transferred",
                        t"The ownership of the community `{community}` has successfully been transferred to `{transfer_jumpedia_user}`!",
                        message_status=messaging.MessageStatus.SUCCESS,
                        additional=t"The rank of `{current_community_user}` has been set to `{CommunityRank.ADMINISTRATOR}`.",
                    )
                )
            else:
                await interaction.response.send_message(
                    messaging.layout(
                        f"Ownership Transfer Aborted",
                        t"The ownership of the community `{community}` stays in your hands, because the name entered was not the specified user's name (`{transfer_jumpedia_user}`)!",
                        messaging.MessageStatus.WARNING,
                    )
                )

        await interaction.response.send_modal(
            modal.ConfirmByEnteringModal(
                interaction,
                f"Confirm Ownership Transfer",
                f"Enter the other user's name to confirm:",
                lambda s: s == transfer_jumpedia_user.name,
                after_submit,
            )
        )
