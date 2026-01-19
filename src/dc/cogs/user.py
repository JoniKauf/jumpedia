import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapting._community import CommunityAdapter
from adapting._user import UserAdapter
from adapting.interaction import InteractionAdapter
from dc_utils import message, shortcuts
from utils import text
from utils.rank import AnyRankT, CommunityRank, JumpediaRank, ServerRank

from ..discord_utils import user as user_


class UserCog(cmds.GroupCog, group_name="user"):

    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Get information about a user.")
    async def info(
        self, interaction: dc.Interaction, user: dc.User | None = None
    ) -> None:
        ia = InteractionAdapter(interaction)

        jumpedia_user = shortcuts.get_or_create_specified_or_current_jumpedia_user(
            ia, user
        )
        jumpedia = jumpedia_user.jumpedia

        NOT_IN_COMMUNITY = "<Not executed in a community>"

        community_s = jumpedia._o.get_community_by_server_id(ia._c, ia.current_server.id)
        community_user = (
            shortcuts.get_or_create_specified_or_current_community_user(
                CommunityAdapter(community_s, jumpedia), jumpedia_user
            )
            if community_s is not None
            else None
        )

        community_rank = NOT_IN_COMMUNITY
        selected_list = NOT_IN_COMMUNITY

        if community_user is not None:
            community_rank = community_user.community_rank
            selected_list = community_user.get_selected_list()
            selected_list = selected_list.name if selected_list is not None else None

        server_rank: ServerRank | str = (
            ia.current_member.server_rank
            if isinstance(ia._o.user, dc.Member)
            else "<Not executed on a server>"
        )

        rank_info: list[tuple[str, AnyRankT | str]] = [
            ("Server Rank", server_rank),
            ("Community Rank", community_rank),
            ("Jumpedia Rank", jumpedia_user.jumpedia_rank),
        ]

        await interaction.response.send_message(
            message.layout(
                "User Info",
                text.join_t(
                    "\n",
                    (
                        t"**{k}**: {v}"
                        for k, v in (
                            ("Name", jumpedia_user.name),
                            ("Selected List", selected_list),
                            *rank_info,
                        )
                    ),
                ),
                message.MessageStatus.INFO,
            )
        )

    @acmds.command()
    async def set_selected_list(
        self,
        interaction: dc.Interaction,
        list: str | None = None,
        user: dc.User | None = None,
    ) -> None:
        user_.validate_allowed_for_others(interaction, user, CommunityRank.MODERATOR)

        ia = InteractionAdapter(interaction)

        jumpedia = ia.jumpedia
        community = jumpedia.get()

        set_community_user = community.get_or_create_community_user(
            jumpedia.get_or_create_jumpedia_user_or_current(
                None if user is None else UserAdapter(user, ia)
            )
        )

        ia_community_user = community.get_or_create_current_community_user()

        list_obj = set_community_user.set_selected_list(list, ia_community_user)

        await interaction.response.send_message(
            message.layout(
                "Selected List Set",
                (
                    t"Your selected list "
                    if ia_community_user == set_community_user
                    else t"The selected list of the user {set_community_user:,} "
                )
                + t"has successfully been set to {list_obj:,}!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Set the community rank of a user.")
    async def set_community_rank(
        self, interaction: dc.Interaction, user: dc.User, community_rank: CommunityRank
    ) -> None:
        community_user = shortcuts.get_or_create_specified_or_current_community_user(
            InteractionAdapter(interaction), user
        )

        await interaction.response.send_message(
            community_user.set_community_rank(
                community_rank,
                shortcuts.get_or_create_specified_or_current_community_user(
                    community_user.community, None
                ),
            )
        )

    @acmds.command(description="Set the jumpedia rank of a user.")
    async def set_jumpedia_rank(
        self, interaction: dc.Interaction, user: dc.User, rank: JumpediaRank
    ) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia = ia.jumpedia

        set_jumpedia_user = jumpedia.get_or_create_jumpedia_user(UserAdapter(user, ia))

        await interaction.response.send_message(
            set_jumpedia_user.set_jumpedia_rank(
                rank, jumpedia.get_or_create_current_jumpedia_user()
            )
        )
