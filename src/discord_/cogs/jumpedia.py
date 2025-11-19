from string.templatelib import Template

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters.interaction import InteractionAdapter
from discord_.utils_ import group
from structures.community import Community
from structures.jumpedia import Jumpedia
from utils import text
from utils.rank import CommunityRank, JumpediaRank, ServerRank

from ..errors import FeedbackError
from ..utils_ import messaging, modal, predicate


class JumpediaCog(cmds.GroupCog, name="jumpedia"):
    @acmds.command()
    async def super_secret_command(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        JONI_ID = 679564566769827841

        if interaction.user.id != JONI_ID:
            raise FeedbackError("No.", t"YOU SHALL NOT PASS!\n-# Gandalf said calmly")

        ia.jumpedia.get_or_create_current_jumpedia_user(override_jumpedia_rank=JumpediaRank.JONIKAUF)

        await interaction.response.send_message(
            messaging.layout(
                "Hi Joni.",
                t"Everything was setup properly.",
                messaging.MessageStatus.INFO,
            )
        )

    get_group = group.get_get_group(Jumpedia)

    @get_group.command(name="communities", description="Get all communities.")
    async def get_communities(self, interaction: dc.Interaction) -> None:
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

    create_group = group.get_create_group(Jumpedia, CommunityRank.OWNER)

    @create_group.command(name="community", description="Create a new community.")
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    async def create_community(
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

    delete_group = acmds.Group(
        name="delete", description="Delete objects that belong to the Jumpediaverse."
    )

    @delete_group.command(name="community", description="Delete a community.")
    async def delete_community(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)
        community = ia.jumpedia.get_current_community()

        await modal.delete_structure_confirmation(
            ia._s,
            Community,
            community._s.name,
            lambda _: ia.jumpedia.delete_community(community.name),
        )

    connect_group = acmds.Group(
        name="connect", description="Connect objects that belong to the metaverse."
    )

    @connect_group.command(
        name="community", description="Connect an existing community to this server."
    )
    @acmds.check(predicate.rank_required(ServerRank.SERVER_OWNER))
    async def connect_community(
        self, interaction: dc.Interaction, community_name: str
    ) -> None:
        ia = InteractionAdapter(interaction)

        community = ia.jumpedia.add_community_to_current_server(community_name)

        await interaction.response.send_message(
            messaging.layout(
                "Community Connected",
                t"This server has successfully been connected to the community `{community.name:p}`!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    disconnect_group = acmds.Group(
        name="disconnect",
        description="Disconnect objects that belong to the metaverse.",
    )

    @disconnect_group.command(
        name="community", description="Disconnect a community from this server."
    )
    @acmds.check(predicate.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect_community(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        community = ia.jumpedia.remove_community_from_current_server()

        await interaction.response.send_message(
            messaging.layout(
                "Community Disconnected",
                t"The community `{community.name:p}` has successfully been disconnected from this server!",
                messaging.MessageStatus.SUCCESS,
            )
        )
