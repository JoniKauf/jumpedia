import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import messagetools, predicates
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

        community = Jumpedia().create_community(ia.user.id, ia.user.global_name or ia.user.name, ia.id, name)

        await messagetools.success(
            ia,
            "Community Created",
            f"The community with the name `{community.name}` was successfully created and is now bound to this server!"
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
            "New Community Host",
            f"This server now successfully hosts the community `{community.name}`!"
        )
        
    @acmds.command(description="Disconnect a community from this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect(self, ia: dc.Interaction) -> None:
        assert ia.guild_id is not None

        community = Jumpedia().get_community_by_server_id(ia.guild_id)

        if community is None:
            raise fbe.TemporaryFeedbackError("This community doesn't host a community.")

        community.remove_from_server(ia.guild_id)

        await messagetools.success(
            ia,
            "Community Evicted",
            f"The community `{community.name}` has successfully been evicted from this server!"
        )


async def setup(bot: cmds.Bot):
    await bot.add_cog(CommunityCog(bot))