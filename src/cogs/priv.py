from enum import Enum
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import helpers, modals, msg, predicates, feedbackerrors as fbe, views, required
from discordtools.context import Context
from structures import ranks
from structures.ranks import CommunityRank, MetaRank, ServerRank
from utils import text

class PrivCog(cmds.GroupCog, group_name="priv"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    community_group = acmds.Group(name="community", description="Edit things about communities")

    @community_group.command(name="create", description="Create a new community.")
    @acmds.check(predicates.rank_required(MetaRank.META_ADMIN))
    async def create_community(self, ia: dc.Interaction, community_name: str) -> None:
        ctx = Context(ia)

        community = ctx.jumpedia.create_community(ia.user, ctx.server.id, community_name)

        await ia.response.send_message(msg.layout(
            "Community Created",
            f"The community `{community.name}` was successfully created and is now connected to this server!",
            msg.MsgFeedback.SUCCESS
        ))

    @community_group.command(name="delete", description="Delete a community.")
    @acmds.check(predicates.rank_required(CommunityRank.OWNER))
    async def delete_community(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        community = ctx.community

        async def after_submit(ia: dc.Interaction, correct: bool) -> None:
            if correct:
                ctx.jumpedia.delete_community(community.name)

                return await ia.response.send_message(msg.layout(
                    "Community Deleted",
                    f"The community `{community.name}` has successfully been deleted!",
                    msg.MsgFeedback.SUCCESS
                ))
            
            await ia.response.send_message(msg.layout(
                "Community Deletion Aborted",
                f"The community `{community.name}` has **not** been deleted because the name entered is not correct!",
                msg.MsgFeedback.WARNING
            ))

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            ia,
            "Confirm Community Deletion",
            "Enter the community's name to confirm",
            lambda s: s == community.name,
            after_submit
        ))


    @community_group.command(description="Connect a community to this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def connect(self, ia: dc.Interaction, community_name: str) -> None:
        ctx = Context(ia)
        server = ctx.server

        community = required.community_this_server(ctx.jumpedia.get_community_by_name(community_name))
    
        community.add_to_server(server.id)

        await ia.response.send_message(msg.layout(
            "Community Connected",
            f"This server has successfully been connected with the community `{community.name}`!",
            msg.MsgFeedback.SUCCESS
        ))
        
    @community_group.command(description="Disconnect a community from this server.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_OWNER))
    async def disconnect(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        
        community = ctx.community

        community.remove_from_server(ctx.server.id)

        await ia.response.send_message(msg.layout(
            "Community Disconnected",
            f"The community `{community.name}` has successfully been disconnected from this server!",
            msg.MsgFeedback.SUCCESS
        ))

    @community_group.command(description="Change the default list that is used when a user doesn't have one set.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_ADMINISTRATOR))
    async def set_default_selected_list(self, ia: dc.Interaction, list_name: str | None = None) -> None:
        ctx = Context(ia)

        community = ctx.community

        if list_name is not None:
            list_name = required.list(community.get_list_by_name(list_name)).name

        community.set_default_selected_list(list_name)

        await ia.response.send_message(msg.layout(
            "Default Selected List Set",
            f"The default selected list has successfully been changed to `{list_name}`!"
            if list_name is not None else
            "The default selected list has successfully been changed to be unset, meaning that users are forced to select one.",
            msg.MsgFeedback.SUCCESS
        ))
    
    user_group = acmds.Group(name="user", description="Edit things about users.")

    PromoteRanks = Enum('PromoteRanks', [
        (rank.name, rank) for rank in CommunityRank.iter()
        if rank is not CommunityRank.LOWEST
    ] + [])  # For some reason adding a second list removes type errors
    
    @user_group.command()
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

        await ia.response.send_message(msg.layout(
            "User Promoted",
            f"The user `{other_user_name}` has successfully been promoted to `{new_rank}`!",
            msg.MsgFeedback.SUCCESS
        ))


    DemoteRanks = Enum('DemoteRanks', [
        (rank.name, rank) for rank in CommunityRank.iter()
        if rank is not CommunityRank.HIGHEST
    ] + [])

    @user_group.command()
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

        await ia.response.send_message(msg.layout(
            "User Demoted",
            f"The user `{other_user_name}` has successfully been demoted to `{new_rank}`!",
            msg.MsgFeedback.SUCCESS
        ))


    list_group = acmds.Group(name="list", description="Edit things about lists.")

    @list_group.command(name="create", description="Create a new list.")
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def create_list(self, ia: dc.Interaction, list_name: str) -> None:
        ctx = Context(ia)

        new_list = ctx.community.create_list(list_name)

        await ia.response.send_message(msg.layout(
            "List Created",
            f"The list `{new_list.name}` has been created successfully!",
            msg.MsgFeedback.SUCCESS
        ))

    @list_group.command(name="delete", description="Delete a list.")
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def delete_list(self, ia: dc.Interaction, list_name: str) -> None:
        ctx = Context(ia)

        list = required.list(ctx.community.get_list_by_name(list_name))

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                ctx.community.delete_list(list_name)

                return await ia.response.send_message(msg.layout(
                    "List Deleted",
                    f"The list `{list.name}` has successfully been deleted!",
                    msg.MsgFeedback.SUCCESS
                ))

            await ia.response.send_message(msg.layout(
                "List Deletion Aborted",
                f"The list `{list.name}` has **not** been deleted because the name entered is not correct!",
                msg.MsgFeedback.WARNING
            ))

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            ia,
            "Confirm List Deletion",
            "Re-Enter the list's name to confirm",
            lambda s: s == list.name,
            after_submit
        ))

            



async def setup(bot: cmds.Bot):
    await bot.add_cog(PrivCog(bot))