from enum import Enum
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import messaging, modals, predicates, feedbackerrors as fbe, utils, views, required
from structure_bridge.context import Context
from structures.list.list import List

class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
    
    @acmds.command(description="Show information about the community.")
    async def info(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)

        community = ctx.community
        
        default_selected_list = community.get_default_selected_list()
        default_selected_list_name = default_selected_list.name if default_selected_list is not None else "None"
        
        await ia.response.send_message(messaging.layout(
            "Community Info",
            '\n'.join(
                f"**{k}:** {v}" for k, v in [
                    ("Name", community.name),
                    ("Server Count", len(community.get_server_ids())),
                    ("List Count", len(community.get_lists())),
                    ("Default Selected List", default_selected_list_name)
                ]
            ),
            messaging.MessageStatus.INFO
        ))


    get_group = acmds.Group(name="get", description="Get objects of the community.")

    @get_group.command(name="lists", description="Get all lists of the community.")
    async def list_lists(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        community = ctx.community

        await ia.response.send_message(messaging.layout(
            "All Lists",
            ','.join(f"- {list.name}" for list in community.get_lists()) or "None",
            messaging.MessageStatus.INFO
        ))


    set_group = acmds.Group(name="set", description="Set values for objects of the community.")

    @set_group.command(name="default_selected_list", description="Set the default selected list of the community.")
    @acmds.check(predicates.rank_required(ServerRank.SERVER_ADMINISTRATOR))
    async def set_default_selected_list(self, ia: dc.Interaction, list: str | None = None) -> None:
        ctx = Context(ia)

        community = ctx.community

        selected_list = ctx.get_selected_list(list)

        community.set_default_selected_list(selected_list.id)

        await ia.response.send_message(messaging.layout(
            "Default Selected List Set",
            f"The default selected list has successfully been changed to `{list}`!"
            if list is not None else
            "The default selected list has successfully been changed to be unset, meaning that users are forced to select one.",
            messaging.MessageStatus.SUCCESS
        ))


    SetRanks = Enum('PromoteRanks', [
        (rank.name, rank) for rank in CommunityRank.iter()
    ] + [])  # For some reason adding a second list removes type errors
    
    @set_group.command(name="user_community_rank", description="Set a user's community rank.")
    @acmds.rename(other_user="user", rank_enum="rank")
    @acmds.check(predicates.rank_required(ranks.get_offset_rank(CommunityRank.USER, 2)))
    async def user_community_rank(self, ia: dc.Interaction, other_user: dc.User, rank_enum: SetRanks) -> None:
        ctx = Context(ia)

        other_user_id, other_user_name = utils.get_user_id_and_name(other_user)

        other_community_user = ctx.community.create_or_get_community_user(
            other_user.id, other_user_name
        )

        new_rank: CommunityRank = rank_enum.value
        
        if new_rank.power == other_community_user.community_rank.power:
            raise fbe.TemporaryFeedbackError("The new rank for the user is equal to the one they already have.")
        
        community_user = ctx.community_user

        rank_below_mine = ranks.get_offset_rank(community_user.highest_rank, -1)
        
        if new_rank.power > rank_below_mine.power:
            raise fbe.TemporaryFeedbackError("The rank you want to give to that user is too high. You must be higher than the rank you want to give.")

        ctx.community.change_community_user_community_rank(
            other_user_id, other_user_name, new_rank
        )

        what_moted = "promoted" if new_rank.power > other_community_user.community_rank.power else "demoted"

        await ia.response.send_message(messaging.layout(
            f"User {what_moted.title()}",
            f"The user `{other_user_name}` has successfully been {what_moted} to `{new_rank}`!",
            messaging.MessageStatus.SUCCESS
        ))


    create_group = acmds.Group(name="create", description="Create new objects for the community.")

    @create_group.command(name="list", description="Create a new list.")
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def create_list(self, ia: dc.Interaction, list_name: str) -> None:
        ctx = Context(ia)

        new_list = ctx.community.create_list(list_name)

        await ia.response.send_message(messaging.layout(
            "List Created",
            f"The list `{new_list.name}` has been created successfully!",
            messaging.MessageStatus.SUCCESS
        ))
    

    delete_group = acmds.Group(name="delete", description="Delete objects from the community.")

    @delete_group.command(name="list", description="Delete a list from the community.")
    @acmds.check(predicates.rank_required(CommunityRank.ADMINISTRATOR))
    async def delete_list(self, ia: dc.Interaction, list_name: str) -> None:
        ctx = Context(ia)

        list = required.structure_with_name(ctx.community.get_list_by_name(list_name), List)

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                ctx.community.delete_list(list_name)

                return await ia.response.send_message(messaging.layout(
                    "List Deleted",
                    f"The list `{list.name}` has successfully been deleted!",
                    messaging.MessageStatus.SUCCESS
                ))

            await ia.response.send_message(messaging.layout(
                "List Deletion Aborted",
                f"The list `{list.name}` has **not** been deleted because the name entered is not correct!",
                messaging.MessageStatus.WARNING
            ))

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            ia,
            "Confirm List Deletion",
            "Re-Enter the list's name to confirm",
            lambda s: s == list.name,
            after_submit
        ))
  



async def setup(bot: cmds.Bot):
    await bot.add_cog(CommunityCog(bot))