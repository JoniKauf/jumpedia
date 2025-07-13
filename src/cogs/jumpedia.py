import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._jumpedia import JumpediaAdapter
from errors.feedback import feedbacks
from database import queries
from discord_structures import modals, predicates
from database.typed import Tables as Tables
from discordtools import messaging
from ranks import CommunityRank, JumpediaRank, ServerRank


class JumpediaCog(cmds.GroupCog, group_name="jumpedia"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def super_secret_command(self, interaction: dc.Interaction) -> None:
        JONI_ID = 679564566769827841

        
        
        if interaction.user.id != JONI_ID:
            raise feedbacks.temp("You are not permitted to use this command!")
        
        jumpedia.get_or_create_current_jumpedia_user(JumpediaRank.JONIKAUF)

        await interaction.response.send_message(messaging.layout(
            "Hi Joni.",
            "Everything was setup properly.",
            messaging.MessageStatus.INFO
        ))


    get_group = acmds.Group(name="get", description="Get objects that belong to Jumpedia.")
    
    @get_group.command(name="communities", description="Get all communities.")
    async def show_communities(self, interaction: dc.Interaction) -> None:
        communities = JumpediaAdapter(interaction).get_communities()

        await interaction.response.send_message(messaging.layout(
            "All Communities",
            '\n'.join(f"- {community.name}" for community in communities) or "None",
            messaging.MessageStatus.INFO
        ))


    create_group = acmds.Group(name="create", description="Create objects that belong to the metaverse.")

    @create_group.command(name="community", description="Create a new community.")
    @acmds.check(predicates.rank_required(JumpediaRank.META_ADMIN))
    async def create_community(self, interaction: dc.Interaction, community_name: str) -> None:
        ctx = Context(interaction)

        community = ctx.jumpedia.create_community(interaction.user, ctx.server.id, community_name)

        await interaction.response.send_message(messaging.layout(
            "Community Created",
            f"The community `{community.name}` was successfully created and is now connected to this server!",
            messaging.MessageStatus.SUCCESS
        ))


    delete_group = acmds.Group(name="delete", description="Delete objects that belong to the metaverse.")

    @delete_group.command(name="community", description="Delete a community.")
    @acmds.check(predicates.rank_required(CommunityRank.OWNER))
    async def delete_community(self, interaction: dc.Interaction) -> None:
        ctx = Context(interaction)
        community = ctx.community

        async def after_submit(interaction: dc.Interaction, correct: bool) -> None:
            if correct:
                ctx.jumpedia.delete_community(community.name)

                return await interaction.response.send_message(messaging.layout(
                    "Community Deleted",
                    f"The community `{community.name}` has successfully been deleted!",
                    messaging.MessageStatus.SUCCESS
                ))
            
            await interaction.response.send_message(messaging.layout(
                "Community Deletion Aborted",
                f"The community `{community.name}` has **not** been deleted because the name entered is not correct!",
                messaging.MessageStatus.WARNING
            ))

        await interaction.response.send_modal(modals.ConfirmByEnteringModal(
            interaction,
            "Confirm Community Deletion",
            "Enter the community's name to confirm",
            lambda s: s == community.name,
            after_submit
        ))

    connect_group = acmds.Group(name="connect", description="Connect objects that belong to the metaverse.")

    @connect_group.command(name="community", description="Connect an existing community to this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def connect_community(self, interaction: dc.Interaction, community_name: str) -> None:
        ctx = Context(interaction)
        server = ctx.server

        community = required.server_with_community(ctx.jumpedia.get_community_by_name(community_name))
    
        community.add_to_server(server.id)

        await interaction.response.send_message(messaging.layout(
            "Community Connected",
            f"This server has successfully been connected with the community `{community.name}`!",
            messaging.MessageStatus.SUCCESS
        ))
    
    
    disconnect_group = acmds.Group(name="disconnect", description="Disconnect objects that belong to the metaverse.")

    @disconnect_group.command(name="community", description="Disconnect a community from this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect_community(self, interaction: dc.Interaction) -> None:
        ctx = Context(interaction)
        
        community = ctx.community

        community.remove_from_server(ctx.server.id)

        await interaction.response.send_message(messaging.layout(
            "Community Disconnected",
            f"The community `{community.name}` has successfully been disconnected from this server!",
            messaging.MessageStatus.SUCCESS
        ))


async def setup(bot: cmds.Bot):
    await bot.add_cog(JumpediaCog(bot))