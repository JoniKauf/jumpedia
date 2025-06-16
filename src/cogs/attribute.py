import builtins
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discord_structures import predicates
from discordtools import messaging, feedbackerrors as fbe
from bridges.context import Context

class AttributeCog(cmds.GroupCog, group_name="attribute"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def list_attributes(self, ia: dc.Interaction) -> None:
        list = Context(ia).get_selected_list
        
        result: builtins.list[str] = []

        for attr_type, attr_coll in list.get_attributes_categorized():
            result.append(
                f"__**{attr_type.__structure_name__.title()}**__\n" +
                ('\n'.join(f"- {attr.name}" for attr in attr_coll) or "None")
            )

        await ia.response.send_message(messaging.layout(
            "All Attributes",
            '\n\n'.join(result),
            messaging.MessageStatus.INFO
        ))


async def setup(bot: cmds.Bot):
    await bot.add_cog(AttributeCog(bot))