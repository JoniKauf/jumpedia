import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from database import queries
from discordtools import msg, predicates, feedbackerrors as fbe
from database.strong import Tables as TBL
from discordtools.context import Context
from structures.ranks import MetaRank

class MetaCog(cmds.GroupCog, group_name="meta"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def i_am_joni(self, ia: dc.Interaction) -> None:
        JONI_ID = 679564566769827841
        JONI_NAME = "JoniKauf"

        ctx = Context(ia)

        if ia.user.id != JONI_ID:
            raise fbe.TemporaryFeedbackError("You are not Joni...")

        ctx.jumpedia.create_or_get_user(ia.user.id, JONI_NAME)
        ctx.jumpedia.change_user_meta_rank(ia.user.id, JONI_NAME, MetaRank.JONIKAUF)

        await ia.response.send_message(msg.layout(
            "Yes, you are Joni.",
            "Everything setup properly.",
            msg.MsgFeedback.INFO
        ))


async def setup(bot: cmds.Bot):
    await bot.add_cog(MetaCog(bot))