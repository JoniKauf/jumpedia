import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from utils import required
from database import queries
from discord_structures import modals, predicates
from discordtools import messaging, feedbackerrors as fbe
from database.typed import Tables as TBL
from bridges.context import Context
from structures.ranks import CommunityRank, MetaRank, ServerRank


class MetaCog(cmds.GroupCog, group_name="meta"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def i_am_joni(self, ia: dc.Interaction) -> None:
        JONI_ID = 679564566769827841
        JONI_NAME = "JoniKauf"

        ctx = Context(ia)

        if ia.user.id != JONI_ID:
            raise fbe.TemporaryFeedbackError("You are not Joni...")

        ctx.jumpedia.create_or_get_user(ia.user.id, JONI_NAME)
        ctx.jumpedia.change_user_meta_rank(ia.user.id, JONI_NAME, MetaRank.JONIKAUF)

        await ia.response.send_message(messaging.layout(
            "Yes, you are Joni.",
            "Everything setup properly.",
            messaging.MessageStatus.INFO
        ))


    get_group = acmds.Group(name="list", description="Get objects that belong to the metaverse.")
    
    @get_group.command(name="communities", description="Get all communities.")
    async def show_communities(self, ia: dc.Interaction) -> None:
        communities = Context(ia).jumpedia.get_communities()

        await ia.response.send_message(messaging.layout(
            "All Communities",
            '\n'.join(f"- {community.name}" for community in communities) or "None",
            messaging.MessageStatus.INFO
        ))


    create_group = acmds.Group(name="create", description="Create objects that belong to the metaverse.")

    @create_group.command(name="community", description="Create a new community.")
    @acmds.check(predicates.rank_required(MetaRank.META_ADMIN))
    async def create_community(self, ia: dc.Interaction, community_name: str) -> None:
        ctx = Context(ia)

        community = ctx.jumpedia.create_community(ia.user, ctx.server.id, community_name)

        await ia.response.send_message(messaging.layout(
            "Community Created",
            f"The community `{community.name}` was successfully created and is now connected to this server!",
            messaging.MessageStatus.SUCCESS
        ))


    delete_group = acmds.Group(name="delete", description="Delete objects that belong to the metaverse.")

    @delete_group.command(name="community", description="Delete a community.")
    @acmds.check(predicates.rank_required(CommunityRank.OWNER))
    async def delete_community(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        community = ctx.community

        async def after_submit(ia: dc.Interaction, correct: bool) -> None:
            if correct:
                ctx.jumpedia.delete_community(community.name)

                return await ia.response.send_message(messaging.layout(
                    "Community Deleted",
                    f"The community `{community.name}` has successfully been deleted!",
                    messaging.MessageStatus.SUCCESS
                ))
            
            await ia.response.send_message(messaging.layout(
                "Community Deletion Aborted",
                f"The community `{community.name}` has **not** been deleted because the name entered is not correct!",
                messaging.MessageStatus.WARNING
            ))

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            ia,
            "Confirm Community Deletion",
            "Enter the community's name to confirm",
            lambda s: s == community.name,
            after_submit
        ))

    connect_group = acmds.Group(name="connect", description="Connect objects that belong to the metaverse.")

    @connect_group.command(name="community", description="Connect an existing community to this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def connect_community(self, ia: dc.Interaction, community_name: str) -> None:
        ctx = Context(ia)
        server = ctx.server

        community = required.server_with_community(ctx.jumpedia.get_community_by_name(community_name))
    
        community.add_to_server(server.id)

        await ia.response.send_message(messaging.layout(
            "Community Connected",
            f"This server has successfully been connected with the community `{community.name}`!",
            messaging.MessageStatus.SUCCESS
        ))
    
    
    disconnect_group = acmds.Group(name="disconnect", description="Disconnect objects that belong to the metaverse.")

    @disconnect_group.command(name="community", description="Disconnect a community from this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect_community(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        
        community = ctx.community

        community.remove_from_server(ctx.server.id)

        await ia.response.send_message(messaging.layout(
            "Community Disconnected",
            f"The community `{community.name}` has successfully been disconnected from this server!",
            messaging.MessageStatus.SUCCESS
        ))


async def setup(bot: cmds.Bot):
    await bot.add_cog(MetaCog(bot))