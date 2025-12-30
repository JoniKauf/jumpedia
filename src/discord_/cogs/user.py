import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._list import ListAdapter
from adapters._user import UserAdapter
from adapters.errors import ServerNotConnectedToACommunityFeedbackError
from adapters.interaction import InteractionAdapter
from discord_.errors import FeedbackError
from discord_.utils_ import messaging
from src.discord_.utils_ import shortcuts
from utils import text
from utils.rank import AnyRankT, CommunityRank, JumpediaRank, ServerRank

from ..utils_ import user as user_


class UserCog(cmds.GroupCog, group_name="user"):

    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Get information about a user.")
    async def info(
        self, interaction: dc.Interaction, user: dc.User | None = None
    ) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia = ia.jumpedia
        jumpedia_user = jumpedia.get_or_create_jumpedia_user_or_current(
            UserAdapter(user, ia) if user is not None else None
        )

        jumpedia_rank: JumpediaRank = jumpedia_user.jumpedia_rank
        community_rank: CommunityRank | None = None
        server_rank: ServerRank | None = None
        selected_list: ListAdapter | None = None

        try:
            community_user = (
                jumpedia.get_current_community().get_or_create_community_user(
                    jumpedia_user
                )
            )
        except ServerNotConnectedToACommunityFeedbackError:
            pass
        else:
            community_rank = community_user.community_rank
            selected_list = community_user.get_selected_list()

        try:
            server_rank = ia.current_member.server_rank
        except FeedbackError:
            pass

        community = InteractionAdapter(interaction).jumpedia.get_current_community()

        community.get_or_create_current_community_user().most_powerful_rank

        rank_info: list[tuple[str, AnyRankT | str]] = [
            ("Server Rank", server_rank or "<Not on a server>"),
            ("Community Rank", community_rank or "<Not in a community>"),
            ("Jumpedia Rank", jumpedia_rank),
        ]

        await interaction.response.send_message(
            messaging.layout(
                "User Info",
                text.join_t(
                    "\n",
                    (
                        t"**{k}**: {v}"
                        for k, v in (
                            ("Name", jumpedia_user.name),
                            ("Selected List", selected_list or None),
                            *rank_info,
                        )
                    ),
                ),
                messaging.MessageStatus.INFO,
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
        community = jumpedia.get_current_community()

        set_community_user = community.get_or_create_community_user(
            jumpedia.get_or_create_jumpedia_user_or_current(
                None if user is None else UserAdapter(user, ia)
            )
        )

        ia_community_user = community.get_or_create_current_community_user()

        list_obj = set_community_user.set_selected_list(list, ia_community_user)

        await interaction.response.send_message(
            messaging.layout(
                "Selected List Set",
                (
                    t"Your selected list "
                    if ia_community_user == set_community_user
                    else t"The selected list of the user `{set_community_user}` "
                )
                + t"has successfully been set to `{list_obj}`!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Set the community rank of a user.")
    async def set_community_rank(
        self, interaction: dc.Interaction, user: dc.User, community_rank: CommunityRank
    ) -> None:
        community_user = shortcuts.get_or_create_specified_or_current_community_user(InteractionAdapter(interaction), user)

        await interaction.response.send_message(
            community_user.set_community_rank(
                community_rank, shortcuts.get_or_create_specified_or_current_community_user(community_user.community, None)
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
