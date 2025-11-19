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
from structures.user import CommunityUser, JumpediaUser
from utils.rank import CommunityRank, ServerRank, JumpediaRank
from utils import text

from ..utils_ import messaging, modal, predicate


class CommunityUserCog(cmds.GroupCog, group_name="community_user"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(name="info")
    async def info(
        self, interaction: dc.Interaction, user: dc.User | None = None
    ) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia = ia.jumpedia

        jumpedia_user = jumpedia.get_or_create_jumpedia_user_or_current(None if user is None else ServerUserAdapter(user, ia))
        community_user = jumpedia.get_current_community().get_or_create_community_user(jumpedia_user)

        data: dict[str, t.Any] = {
            "Name": community_user.name,
            CommunityRank.type_name.title(): community_user.community_rank,
        }

        await interaction.response.send_message(
            messaging.layout(
                "Community User Info",
                Template("\n".join(f"**{k}:** {v}" for k, v in data.items())),
                messaging.MessageStatus.INFO,
            )
        )

    
    set_group = group.get_set_group(CommunityUser)

    @set_group.command(name="rank")
    async def set_rank(self, interaction: dc.Interaction, user: dc.User, rank: CommunityRank) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia = ia.jumpedia
        community = jumpedia.get_current_community()

        set_community_user = community.get_or_create_community_user(
            jumpedia.get_or_create_jumpedia_user(ServerUserAdapter(user, ia))
        )

        await interaction.response.send_message(
            set_community_user.set_community_rank(rank, community.get_or_create_current_community_user())
        )

    @set_group.command(name="selected_list")
    async def set_selected_list(self, interaction: dc.Interaction, list: str | None = None, user: dc.User | None = None) -> None:
        ia = InteractionAdapter(interaction)

        jumpedia = ia.jumpedia
        community = jumpedia.get_current_community()

        community_user = community.get_or_create_community_user(
            jumpedia.get_or_create_jumpedia_user_or_current(None if user is None else ServerUserAdapter(user, ia))
        )
        
        ia_community_user = community.get_or_create_current_community_user()

        community_user.set_community_rank