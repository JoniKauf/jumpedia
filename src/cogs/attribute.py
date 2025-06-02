import builtins
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import msg, predicates, feedbackerrors as fbe
from discordtools.context import Context
from structures.attribute import ATTRIBUTE_TYPES

class AttributeCog(cmds.GroupCog, group_name="attribute"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def catalog(self, ia: dc.Interaction) -> None:
        list = Context(ia).selected_list
        
        result: builtins.list[str] = []

        for attr_type, attr_coll in zip(
            ATTRIBUTE_TYPES, 
            list.get_attributes_split(), 
            strict=True
        ):
            result.append(
                f"__**{attr_type.ATTRIBUTE_TYPE_NAME}**__\n" +
                ('\n'.join(f"- {attr.name}" for attr in attr_coll) or "None")
            )

        await ia.response.send_message(msg.layout(
            "All Attributes",
            '\n\n'.join(result),
            msg.MsgFeedback.INFO
        ))


async def setup(bot: cmds.Bot):
    await bot.add_cog(AttributeCog(bot))