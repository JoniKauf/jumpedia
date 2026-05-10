import typing as t
from string.templatelib import Template
from types import CoroutineType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from _adapters._community import CommunityAdapter
from _adapters.interaction import _InteractionAdapter
from dc_utils import command, confirm, group, message, predicate, shortcuts
from structures.community import Community
from utils import text
from domain.enum.rank import CommunityRank, JumpediaRank, ServerRank

_CommunityRowTs = tuple[
    str,
    tuple[str, ...],
    str,
    str,
    tuple[str, ...],
]

if t.TYPE_CHECKING:
    _CommunityRow = command._BaseRow[*_CommunityRowTs]
else:
    _CommunityRow = command.row_type_factory[*_CommunityRowTs](
        "Name",
        "Lists",
        "Default Selected List",
        "Server Count",
        "Limits",
    )


def _comm_to_row(community: CommunityAdapter) -> _CommunityRow:
    return _CommunityRow(
        community.name,
        tuple(lst.name for lst in community.get_lists()),
        "" if (lst := community.get_default_selected_list(None)) is None else lst.name,
        str(community.get_server_count()),
        tuple(
            f"({name.replace('_', ' ').title()}: {limit})"
            for name, limit in community._o.limits.items()
        ),
    )


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt()
    async def info(self, ia: _InteractionAdapter) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)

        return await command.info(ia, community._o, _comm_to_row(community))

    @acmds.command()
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    @command.adapt()
    async def create(
        self,
        ia: _InteractionAdapter,
        name: str,
        owner: dc.User,
        default_selected_list_name: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        jumpedia = ia.jumpedia

        community = jumpedia.create_community(name, owner, default_selected_list_name)

        return ia.dc.followup.send(
            message.layout(
                "Community Created",
                t"The community {community.name:,} was successfully created and is now connected to this server!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    @command.adapt()
    async def nuke(self, ia: _InteractionAdapter) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)

        return await confirm.confirm_nuke(
            ia,
            community._o,
            lambda: community.jumpedia.delete_community(community.name),
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    @command.adapt()
    async def connect(
        self, ia: _InteractionAdapter, community: str
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community_obj = ia.jumpedia.add_community_to_current_server(community)

        return ia.dc.followup.send(
            message.layout(
                "Community Connected",
                t"This server has successfully been connected to the community {community_obj.name:,}!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    @command.adapt()
    async def disconnect(
        self, ia: _InteractionAdapter
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = ia.jumpedia.remove_community_from_current_server()

        return ia.dc.followup.send(
            message.layout(
                "Community Disconnected",
                t"The community {community.name:,} has successfully been disconnected from this server!",
                message.MessageStatus.SUCCESS,
            )
        )

    # @acmds.command(description="Transfer the ownership of a community to another user.")
    # @acmds.check(predicate.rank_required(CommunityRank.OWNER))
    # @command.adapt(rank_to_specify_user=CommunityRank.OWNER)
    # async def transfer_ownership(
    #     self, ia: InteractionAdapter, user: dc.User
    # ) -> CoroutineType[t.Any, t.Any, t.Any]:
    #     community = shortcuts.get_current_community(ia)
    #     transfer_jumpedia_user = (
    #         shortcuts.get_or_create_specified_or_current_jumpedia_user(
    #             community.jumpedia, user
    #         )
    #     )

    #     CONFIG = confirm.ConfirmConfig()

    #     msg = await ia.dc.followup.send(
    #         message.layout(
    #             "Transfer Ownership?",
    #             t"Are you sure you want to transfer the ownership of {community:,} to {transfer_jumpedia_user:,}?",
    #             additional=t"This action CANNOT be undone!",
    #             paragraphs=confirm.get_confirm_paragraphs(CONFIG),
    #             message_status=message.MessageStatus.WARNING,
    #         ),
    #         wait=True,
    #     )

    #     if not await confirm.emoji_confirm(ia, msg, config=CONFIG):
    #         return msg.edit(
    #             content=message.layout(
    #                 "Ownership Transfer Aborted",
    #                 t"The ownership of the community {community:,} stays in your hands, because the request has been aborted!",
    #                 message.MessageStatus.WARNING,
    #             )
    #         )

    #     return msg.edit(
    #         content=message.layout(
    #             "Ownership Transferred",
    #             t"The ownership of the community {community:,} has successfully been transferred to {transfer_jumpedia_user:,}!",
    #             additional=t"The rank of {ia.ia_user.name:,} has been set to {CommunityRank.ADMINISTRATOR:,}.",
    #             message_status=message.MessageStatus.SUCCESS,
    #         )
    #     )

    community_edit_group = group.create_edit_group(CommunityRank.ADMINISTRATOR)

    @community_edit_group.command(name="default_selected_list")
    @command.adapt()
    async def edit_default_selected_list(
        self, ia: _InteractionAdapter, list: str | None = None
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)

        community.set_default_selected_list(list)

        return ia.dc.followup.send(
            message.layout(
                "Default Selected List Set",
                (
                    t"The default selected list has successfully been changed to {list:,}!"
                    if list is not None
                    else t"The default selected list has successfully been changed to be unset."
                ),
                message.MessageStatus.SUCCESS,
            )
        )


class CommunitiesCog(cmds.GroupCog, group_name="communities"):
    @acmds.command()
    @command.adapt()
    async def browse(
        self, ia: _InteractionAdapter
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        communities = ia.jumpedia.get_communities()

        # TODO Make more efficient for more communities

        return await command.browse(
            ia, Community, tuple(map(_comm_to_row, communities))
        )
