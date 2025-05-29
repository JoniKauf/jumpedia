from enum import Enum
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import helpers, messagetools, predicates, feedbackerrors as fbe, views, required
from discordtools.context import Context
from structures import ranks
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

    PromoteRanks = Enum('PromoteRanks', [
        (rank.name, rank) for rank in CommunityRank.iter()
        if rank not in (CommunityRank.LOWEST, CommunityRank.HIGHEST)
    ] + [
        (rank.name, rank) for rank in MetaRank.iter()
        if rank not in (MetaRank.LOWEST, MetaRank.HIGHEST)
    ])

    DemoteRanks = Enum('DemoteRanks', [
        (rank.name, rank) for rank in CommunityRank.iter()
        if rank is not CommunityRank.HIGHEST
    ] + [
        (rank.name, rank) for rank in MetaRank.iter()
        if rank is not MetaRank.HIGHEST
    ])
    
    @user_group.command()
    @acmds.rename(other_user="user", rank_enum="rank")
    # @acmds.check(predicates.rank_required(CommunityRank.MODERATOR))
    async def promote(self, ia: dc.Interaction, other_user: dc.User, rank_enum: PromoteRanks) -> None:
        ctx = Context(ia)

        other_user_id_name = (other_user.id, helpers.get_user_name(other_user))

        other_community_user = ctx.community.create_or_get_community_user(
            other_user.id, other_user_id_name[1]
        )

        new_rank: CommunityRank | MetaRank = rank_enum.value
        
        if other_community_user.highest_rank.power >= new_rank.power:
            raise fbe.TemporaryFeedbackError("The new rank for the user is lower or equal to the one they already have.")
        
        community_user = ctx.community_user

        rank_below = ranks.get_offset_rank(
            community_user.meta_rank or community_user.community_rank, 
            -1
        )
        
        if new_rank.power > rank_below.power:
            raise fbe.TemporaryFeedbackError("The rank you want to give to that user is too high. You must be higher than the rank you want to give.")

        if isinstance(new_rank, MetaRank):
            ctx.jumpedia.change_user_meta_rank(
                *other_user_id_name, new_rank
            )
        else:
            ctx.community.change_community_user_community_rank(
                *other_user_id_name, new_rank
            )

        await messagetools.success(
            ia,
            "User Promoted",
            f"The user `{other_user_id_name[1]}` has successfully been promoted to `{new_rank}`!"
        )

        

async def setup(bot: cmds.Bot):
    await bot.add_cog(PrivCog(bot))