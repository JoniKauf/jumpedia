import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from discord import ui
from discordtools import msg, predicates, required, views
from structures.community import Community
from discordtools.context import Context
from discordtools import feedbackerrors as fbe


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
        
    @acmds.command(description="List all communities.")
    async def catalog(self, ia: dc.Interaction) -> None:
        communities = Context(ia).jumpedia.get_communities()

        await ia.response.send_message(msg.layout(
            "All Communities",
            '\n'.join(f"- {community.name}" for community in communities) or "None",
            msg.MsgFeedback.INFO
        ))

    
    @acmds.command(description="Show information about a community.")
    @acmds.rename(community_str="community")
    async def info(self, ia: dc.Interaction, community_str: str | None = None) -> None:
        ctx = Context(ia)

        if community_str is None:
            community = ctx.community
        else:
            community = required.community_general(ctx.jumpedia.get_community_by_name(community_str))
        
        default_selected_list = community.get_default_selected_list()
        default_selected_list_name = default_selected_list.name if default_selected_list is not None else "None"
        
        await ia.response.send_message(msg.layout(
            "Community Info",
            '\n'.join(
                f"**{k}:** {v}" for k, v in [
                    ("Name", community.name),
                    ("Server Count", len(community.get_server_ids())),
                    ("List Count", len(community.get_lists())),
                    ("Default Selected List", default_selected_list_name)
                ]
            ),
            msg.MsgFeedback.INFO
        ))
        


async def setup(bot: cmds.Bot):
    await bot.add_cog(CommunityCog(bot))