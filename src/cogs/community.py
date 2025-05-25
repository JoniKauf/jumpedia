import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from discord import ui
from discordtools import messagetools, predicates, views
from structures.community import Community
from structures.context import Context
from structures.jumpedia import Jumpedia
from structures.ranks import MetaRank, ServerRank, CommunityRank
from discordtools import feedbackerrors as fbe


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
        self.interaction_check = predicates.in_guild(None)

    @acmds.command(description="List all communities.")
    async def list(self, ia: dc.Interaction) -> None:
        communities = Jumpedia().get_communities()

        await messagetools.success(
            ia,
            "All Communities",
            '\n'.join(f"- {community.name}" for community in communities),
            show_success=False
        )

    @acmds.command(description="Create a new community.")
    @acmds.check(predicates.rank_required(MetaRank.JONIKAUF))
    async def create(self, ia: dc.Interaction, name: str) -> None:
        assert ia.guild is not None

        community = Jumpedia().create_community(ia.user.id, ia.user.global_name or ia.user.name, ia.guild.id, name)

        await messagetools.success(
            ia,
            "Community Created",
            f"The community with the name `{community.name}` was successfully created and is now connected to this server!"
        )

    @acmds.command(description="Connect a community to this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def connect(self, ia: dc.Interaction, name: str) -> None:
        assert ia.guild_id is not None

        community = Jumpedia().get_community_by_name(name)

        if community is None:
            raise fbe.TemporaryFeedbackError("No community with that name found!")
        
        community.add_to_server(ia.guild_id)

        await messagetools.success(
            ia,
            "Community Connected",
            f"This server has successfully been connected with the community `{community.name}`!"
        )
        
    @acmds.command(description="Disconnect a community from this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect(self, ia: dc.Interaction) -> None:
        assert ia.guild_id is not None

        community = Jumpedia().get_community_by_server_id(ia.guild_id)

        if community is None:
            raise fbe.TemporaryFeedbackError("This server isn't connected to a community.")

        community.remove_from_server(ia.guild_id)

        await messagetools.success(
            ia,
            "Community Disconnected",
            f"The community `{community.name}` has successfully been disconnected from this server!"
        )

    @acmds.command()
    @acmds.check(predicates.rank_required(CommunityRank.OWNER))
    async def delete(self, ia: dc.Interaction) -> None:
        assert ia.guild_id is not None

        community = Jumpedia().get_community_by_server_id(ia.guild_id)

        if community is None:
            raise fbe.TemporaryFeedbackError("This server isn't connected to a community.")
        
        async def on_yes(inner_ia: dc.Interaction) -> bool:
            if inner_ia.user.id != ia.user.id:
                return False
            
            Jumpedia().delete_community(community.id)

            return True
        
        async def on_no(inner_ia: dc.Interaction) -> bool:
            if inner_ia.user.id != ia.user.id:
                return False

            return True
        
        view = views.DangerousConfirm(ia, on_yes, on_no)

        await ia.response.send_message(
            f"Are you sure you want to delete the community `{community.name}`!",
            view=view
        )
        


async def setup(bot: cmds.Bot):
    await bot.add_cog(CommunityCog(bot))