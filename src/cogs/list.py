import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from typing import Optional as Opt
from discordtools import msg, predicates, required
from discordtools.context import Context
from discordtools import feedbackerrors as fbe
from structures.ranks import CommunityRank

class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="List all lists.")
    async def catalog(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        community = ctx.community

        await ia.response.send_message(msg.layout(
            "All Lists",
            ','.join(f"- {list.name}" for list in community.get_lists()) or "None",
            msg.MsgFeedback.INFO
        ))

    @acmds.command(description="Show information about a list.")
    @acmds.rename(list_str="list")
    async def info(self, ia: dc.Interaction, list_str: str | None = None) -> None:
        ctx = Context(ia)

        if list_str is None:
            list = ctx.selected_list
        else:
            list = required.list(ctx.community.get_list_by_name(list_str))
        
        attributes = list.get_attributes_split()

        info = [
            ("Name", list.name),
            ("Static Attribute Count", len(attributes[0])),
            ("Task Count", len(list.get_lists())),
            ("Default Selected List", default_selected_list_name)
        ]

        await ia.response.send_message(msg.layout(
            "Community Info",
            '\n'.join(
                f"**{k}:** {v}" for k, v in 
            ),
            msg.MsgFeedback.INFO
        ))
    
        


async def setup(bot: cmds.Bot):
    await bot.add_cog(ListCog(bot))