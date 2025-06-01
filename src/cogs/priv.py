from enum import Enum
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import helpers, messagetools, modals, predicates, feedbackerrors as fbe, views, required
from discordtools.context import Context
from structures import ranks
from structures.ranks import CommunityRank, MetaRank, ServerRank

class PrivCog(cmds.GroupCog, group_name="priv"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    community_group = acmds.Group(name="community", description="Edit things about communities")

    @community_group.command(name="create", description="Create a new community.")
    @acmds.check(predicates.rank_required(MetaRank.META_ADMIN))
    async def create_community(self, ia: dc.Interaction, name: str) -> None:
        ctx = Context(ia)

        community = ctx.jumpedia.create_community(ia.user, ctx.server.id, name)

        await messagetools.success(
            ia,
            "Community Created",
            f"The community with the name `{community.name}` was successfully created and is now connected to this server!"
        )

    @community_group.command(name="delete", description="Delete a community.")
    @acmds.check(predicates.rank_required(CommunityRank.OWNER))
    async def delete_community(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        community = ctx.community

        async def after_submit(ia: dc.Interaction, correct: bool) -> None:
            if correct:
                ctx.jumpedia.delete_community(ctx.community.id)

                return await messagetools.success(
                    ia,
                    "Community Deleted",
                    f"The community `{community.name}` has successfully been deleted!"
                )
            
            await messagetools.success(
                ia,
                "Community Deletion Aborted",
                f"The community `{community.name}` has **not** been deleted because the name entered is not correct!"
            )

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            "Enter the community's name to confirm",
            community.name,
            after_submit,
            10
        ))


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

    
    list_group = acmds.Group(name="user", description="Edit things about users.")

    PromoteRanks = Enum('PromoteRanks', [
        (rank.name, rank) for rank in CommunityRank.iter()
        if rank not in (CommunityRank.LOWEST, CommunityRank.HIGHEST)
    ] + [])  # For some reason adding a second list removes type errors
    
    @list_group.command()
    @acmds.rename(other_user="user", rank_enum="rank")
    @acmds.check(predicates.rank_required(ranks.get_offset_rank(CommunityRank.USER, 2)))
    async def promote(self, ia: dc.Interaction, other_user: dc.User, rank_enum: PromoteRanks) -> None:
        ctx = Context(ia)

        other_user_id, other_user_name = helpers.get_user_id_and_name(other_user)

        other_community_user = ctx.community.create_or_get_community_user(
            other_user.id, other_user_name
        )

        new_rank: CommunityRank = rank_enum.value
        
        if new_rank.power <= other_community_user.community_rank.power:
            raise fbe.TemporaryFeedbackError("The new rank for the user is lower or equal to the one they already have.")
        
        community_user = ctx.community_user

        rank_below_mine = ranks.get_offset_rank(community_user.highest_rank, -1)
        
        if new_rank.power > rank_below_mine.power:
            raise fbe.TemporaryFeedbackError("The rank you want to give to that user is too high. You must be higher than the rank you want to give.")

        ctx.community.change_community_user_community_rank(
            other_user_id, other_user_name, new_rank
        )

        await messagetools.success(
            ia,
            "User Promoted",
            f"The user `{other_user_name}` has successfully been promoted to `{new_rank}`!"
        )


    DemoteRanks = Enum('DemoteRanks', [
        (rank.name, rank) for rank in CommunityRank.iter()
        if rank is not CommunityRank.HIGHEST
    ] + [])

    @list_group.command()
    @acmds.rename(other_user="user", rank_enum="rank")
    @acmds.check(predicates.rank_required(ranks.get_offset_rank(CommunityRank.USER, 2)))
    async def demote(self, ia: dc.Interaction, other_user: dc.User, rank_enum: DemoteRanks) -> None:
        ctx = Context(ia)

        other_user_id, other_user_name = helpers.get_user_id_and_name(other_user)

        other_community_user = ctx.community.create_or_get_community_user(
            other_user.id, other_user_name
        )

        new_rank: CommunityRank = rank_enum.value
        
        if new_rank.power >= other_community_user.community_rank.power:
            raise fbe.TemporaryFeedbackError("The new rank for the user is higher or equal to the one they already have.")
        
        community_user = ctx.community_user

        rank_below_mine = ranks.get_offset_rank(community_user.highest_rank, -1)
        
        if new_rank.power > rank_below_mine.power:
            raise fbe.TemporaryFeedbackError("The rank you want to give to that user is too high. You must be higher than the rank you want to give.")

        ctx.community.change_community_user_community_rank(
            other_user_id, other_user_name, new_rank
        )

        await messagetools.success(
            ia,
            "User Promoted",
            f"The user `{other_user_name}` has successfully been promoted to `{new_rank}`!"
        )


    list_group = acmds.Group(name="list", description="Edit things about lists.")

    @list_group.command(name="create", description="Create a new list.")
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def create_list(self, ia: dc.Interaction, name: str) -> None:
        ctx = Context(ia)

        new_list = ctx.community.create_list(name)

        await messagetools.success(
            ia,
            "List Created",
            f"The list `{new_list.name}` has been created successfully!"
        )

    @list_group.command(name="delete", description="Delete a list.")
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def delete_list(self, ia: dc.Interaction, name: str) -> None:
        ctx = Context(ia)

        async def on_yes(inner_ia: dc.Interaction) -> bool:
            ctx.community.delete_list(name)

            return True
        


async def setup(bot: cmds.Bot):
    await bot.add_cog(PrivCog(bot))