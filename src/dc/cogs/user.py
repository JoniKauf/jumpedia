import typing as t
from types import CoroutineType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._community import CommunityAdapter
from adapters._user import UserAdapter
from adapters.interaction import _InteractionAdapter
from dc_utils import command, group, message, shortcuts
from utils.rank import CommunityRank, JumpediaRank, ServerRank

_UserRow = command.row_type_factory[
    str,
    str,
    str,
    str,
    str,
](
    "Name",
    "Selected List",
    "Server Rank",
    "Community Rank",
    "Jumpedia Rank",
)


class UserCog(cmds.GroupCog, group_name="user"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt(rank_to_specify_user=None)
    async def info(
        self, ia: _InteractionAdapter, user: dc.User | None = None
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        jumpedia_user = shortcuts.get_or_create_specified_or_current_jumpedia_user(
            ia, user
        )
        jumpedia = ia.jumpedia

        NOT_IN_COMMUNITY = "<Not executed in a community>"

        tup = jumpedia._o.get_community_by_server_id(ia._c, ia.ia_server.id)

        community_user = (
            shortcuts.get_or_create_specified_or_current_community_user(
                CommunityAdapter(tup[0], jumpedia), jumpedia_user
            )
            if tup is not None
            else None
        )

        community_rank = NOT_IN_COMMUNITY
        selected_list = NOT_IN_COMMUNITY

        if community_user is not None:
            community_rank = community_user.community_rank

            selected_list = community_user.get_selected_list()
            selected_list = (
                selected_list.name if selected_list is not None else str(None)
            )

        server_rank: ServerRank | str = (
            ia.ia_server_member.server_rank
            if isinstance(ia._o.user, dc.Member)
            else "<Not executed on a server>"
        )

        return await command.info(
            ia,
            jumpedia_user._o,
            _UserRow(
                jumpedia_user.name,
                selected_list,
                str(server_rank),
                str(community_rank),
                str(jumpedia_user.jumpedia_rank),
            ),
        )

    user_edit_group = group.create_edit_group(CommunityRank.USER)

    @user_edit_group.command(name="selected_list")
    @command.adapt()
    async def edit_selected_list(
        self,
        ia: _InteractionAdapter,
        list: str | None = None,
        user: dc.User | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        specified_community_user = (
            shortcuts.get_or_create_specified_or_current_community_user(ia, user)
        )

        list_obj = specified_community_user.set_selected_list(list)

        return ia.dc.followup.send(
            message.layout(
                "Selected List Set",
                t"The selected list of the user {specified_community_user:,} has successfully been set to {list_obj:,}!",
                message.MessageStatus.SUCCESS,
            )
        )

    @user_edit_group.command(name="community_rank")
    @command.adapt()
    async def edit_community_rank(
        self, ia: _InteractionAdapter, user: dc.User, community_rank: CommunityRank
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community_user = shortcuts.get_or_create_specified_or_current_community_user(
            ia, user
        )

        return ia.dc.followup.send(
            community_user.set_community_rank(
                community_rank,
                shortcuts.get_or_create_specified_or_current_community_user(
                    community_user.community, None
                ),
            )
        )

    @user_edit_group.command(name="jumpedia_rank")
    @command.adapt(rank_to_specify_user=None)
    async def edit_jumpedia_rank(
        self, ia: _InteractionAdapter, user: dc.User, rank: JumpediaRank
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        jumpedia = ia.jumpedia

        set_jumpedia_user = jumpedia.get_or_create_jumpedia_user(UserAdapter(user, ia))

        return ia.dc.followup.send(set_jumpedia_user.set_jumpedia_rank(rank))
