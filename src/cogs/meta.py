import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from database import queries
from discordtools import messagetools, predicates, feedbackerrors as fbe
from database.strong import Tables as TBL
from structures.ranks import MetaRank

class MetaCog(cmds.GroupCog, group_name="meta"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
        self.interaction_check = predicates.in_guild(None)

    @acmds.command()
    async def i_am_joni(self, ia: dc.Interaction) -> None:
        JONI_ID = 679564566769827841

        if ia.user.id != JONI_ID:
            raise fbe.TemporaryFeedbackError("You are not Joni...")

        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                INSERT INTO {TBL.MetaRank} (
                    {TBL.MetaRank.user_id},
                    {TBL.MetaRank.power}
                )
                VALUES (
                    {h|JONI_ID},
                    {h|MetaRank.JONIKAUF.power}
                )
            """, h.steal())

        await messagetools.success(
            ia,
            "Yes, you are Joni.",
            "Everything setup properly."
        )


async def setup(bot: cmds.Bot):
    await bot.add_cog(MetaCog(bot))