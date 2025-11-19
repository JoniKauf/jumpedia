from string.templatelib import Template
import typing as t
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._user import ServerUserAdapter
from adapters.interaction import InteractionAdapter
from discord_.utils_ import group
from structures.community import Community
from structures.list import List
from structures.user import JumpediaUser
from utils.rank import CommunityRank, ServerRank, JumpediaRank
from utils import text

from ..utils_ import messaging, modal, predicate


class JumpediaUserCog(cmds.GroupCog, group_name="jumpedia_user"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(name="info")
    async def info(
        self, interaction: dc.Interaction, user: dc.User | None = None
    ) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia_user = ia.jumpedia.get_or_create_jumpedia_user_or_current(
            None if user is None else ServerUserAdapter(user, ia)
        )

        data: dict[str, t.Any] = {
            "Name": jumpedia_user.name,
            JumpediaRank.type_name.title(): jumpedia_user.jumpedia_rank,
        }

        await interaction.response.send_message(
            messaging.layout(
                "Jumpedia User Info",
                Template("\n".join(f"**{k}:** {v}" for k, v in data.items())),
                messaging.MessageStatus.INFO,
            )
        )

    
    set_group = group.get_set_group(JumpediaUser)

    @set_group.command(name="rank")
    async def set_rank(self, interaction: dc.Interaction, user: dc.User, rank: JumpediaRank) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia = ia.jumpedia

        set_jumpedia_user = jumpedia.get_or_create_jumpedia_user(ServerUserAdapter(user, ia))
        
        await interaction.response.send_message(
            set_jumpedia_user.set_jumpedia_rank(rank, jumpedia.get_or_create_current_jumpedia_user())
        )


