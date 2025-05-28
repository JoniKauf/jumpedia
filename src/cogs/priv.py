import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import messagetools, predicates, feedbackerrors as fbe, views, required
from discordtools.context import Context
from structures.ranks import CommunityRank, MetaRank, ServerRank

class PrivCog(cmds.GroupCog, group_name="priv"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    community_group = acmds.Group(name="community", description="Edit things about communities")

    @community_group.command(description="Create a new community.")
    @acmds.check(predicates.rank_required(MetaRank.META_ADMIN))
    async def create(self, ia: dc.Interaction, name: str) -> None:
        ctx = Context(ia)

        community = ctx.jumpedia.create_community(ia.user, ctx.server.id, name)

        await messagetools.success(
            ia,
            "Community Created",
            f"The community with the name `{community.name}` was successfully created and is now connected to this server!"
        )

    @community_group.command(description="Connect a community to this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def connect(self, ia: dc.Interaction, name: str) -> None:
        ctx = Context(ia)
        server = ctx.server

        community = required.community(ctx.jumpedia.get_community_by_name(name))
    
        community.add_to_server(server.id)

        await messagetools.success(
            ia,
            "Community Connected",
            f"This server has successfully been connected with the community `{community.name}`!"
        )
        
    @community_group.command(description="Disconnect a community from this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        
        community = ctx.community

        community.remove_from_server(ctx.server.id)

        await messagetools.success(
            ia,
            "Community Disconnected",
            f"The community `{community.name}` has successfully been disconnected from this server!"
        )

    @community_group.command()
    @acmds.check(predicates.rank_required(CommunityRank.OWNER))
    async def delete(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        community = ctx.community

        async def on_yes(inner_ia: dc.Interaction) -> bool:
            if inner_ia.user.id != ia.user.id:
                return False
            
            ctx.jumpedia.delete_community(community.id)
        
            await messagetools.success(
                inner_ia,
                "Community Deleted",
                f"You have successfully deleted the community `{community.name}`!\n\n__Rest In Peace__"
            )

            return True
        
        async def on_no(inner_ia: dc.Interaction) -> bool:
            if inner_ia.user.id != ia.user.id:
                return False

            await messagetools.success(
                inner_ia,
                "Community Spared",
                f"You successfully aborted deleting the community `{community.name}`!",
                success_func=inner_ia.response.edit_message
            )

            return True
        
        view = views.DangerousConfirm(ia, on_yes, on_no)

        await ia.response.send_message(
            f"Are you sure you want to delete the community `{community.name}`!\n### This action cannot be undone!",
            view=view
        )

    
    user_group = acmds.Group(name="user", description="Edit things about users.")

    @acmds.command()
    # @acmds.check(predicates.rank_required(CommunityRank.MODERATOR))
    async def promote(self, ia: dc.Interaction, user: dc.User) -> None:
        pass

async def setup(bot: cmds.Bot):
    await bot.add_cog(PrivCog(bot))