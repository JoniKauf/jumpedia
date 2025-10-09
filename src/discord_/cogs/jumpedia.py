import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from ..errors import FeedbackError
from ...adapters.interaction import InteractionAdapter
from ..structs import modals, predicates
from ..utils import messaging
from ...ranks import CommunityRank, JumpediaRank, ServerRank


class JumpediaCog(cmds.GroupCog, name="jumpedia"):
    @acmds.command()
    async def super_secret_command(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        JONI_ID = 679564566769827841

        if interaction.user.id != JONI_ID:
            raise FeedbackError(
                "No.",
                t"YOU SHALL NOT PASS!\n-# Gandalf said calmly"
            )

        ia.jumpedia.get_or_create_current_jumpedia_user(JumpediaRank.JONIKAUF)

        await interaction.response.send_message(
            messaging.layout(
                "Hi Joni.",
                t"Everything was setup properly.",
                messaging.MessageStatus.INFO,
            )
        )

    get_group = acmds.Group(
        name="get", description="Get objects that belong to Jumpedia."
    )

    @get_group.command(name="communities", description="Get all communities.")
    async def show_communities(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        await interaction.response.send_message(
            messaging.layout(
                "All Communities",
                "\n".join(
                    f"- {community.name}" for community in ia.jumpedia.get_communities()
                )
                or "None",
                messaging.MessageStatus.INFO,
            )
        )

    create_group = acmds.Group(
        name="create", description="Create objects that belong to the metaverse."
    )

    @create_group.command(name="community", description="Create a new community.")
    @acmds.check(predicates.rank_required(JumpediaRank.META_ADMIN))
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
                f"The community `{community.name}` was successfully created "
                "and is now connected to this server!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    delete_group = acmds.Group(
        name="delete", description="Delete objects that belong to the metaverse."
    )

    @delete_group.command(name="community", description="Delete a community.")
    @acmds.check(predicates.rank_required(CommunityRank.OWNER))
    async def delete_community(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)
        community = ia.jumpedia.get_current_community()

        await modals.delete_structure_confirmation(
            ia._interaction, 
            community._community, 
            lambda _: ia.jumpedia.delete_community(community.name)
        )

    connect_group = acmds.Group(
        name="connect", description="Connect objects that belong to the metaverse."
    )

    @connect_group.command(
        name="community", description="Connect an existing community to this server."
    )
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def connect_community(
        self, interaction: dc.Interaction, community_name: str
    ) -> None:
        ia = InteractionAdapter(interaction)

        community = ia.jumpedia.add_community_to_current_server(community_name)

        await interaction.response.send_message(
            messaging.layout(
                "Community Connected",
                f"This server has successfully been connected with "
                f"the community `{community.name}`!",
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
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect_community(self, interaction: dc.Interaction) -> None:
        ia = InteractionAdapter(interaction)

        community = ia.jumpedia.remove_community_from_current_server()

        await interaction.response.send_message(
            messaging.layout(
                "Community Disconnected",
                f"The community `{community.name}` has successfully been "
                "disconnected from this server!",
                messaging.MessageStatus.SUCCESS,
            )
        )

