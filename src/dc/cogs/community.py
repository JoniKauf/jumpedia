import typing as t
from string.templatelib import Template
from types import CoroutineType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._community import CommunityAdapter
from adapters.interaction import InteractionAdapter
from dc_utils import command, confirm, message, predicate, shortcuts
from structures.community import Community
from utils import text
from utils.rank import CommunityRank, JumpediaRank, ServerRank


class _CommunityRow(t.NamedTuple):
    name: str
    lists: tuple[str, ...]
    default_selected_list: str
    server_count: str
    limits: tuple[str, ...]


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

    @acmds.command(description="Show information about the community.")
    @command.adapt()
    async def info(self, ia: InteractionAdapter) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)

        return await command.info(ia, community._o, _comm_to_row(community))

    @acmds.command(description="Create a community.")
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    @command.adapt()
    async def create(
        self,
        ia: InteractionAdapter,
        community_name: str,
        initial_list_name: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        jumpedia = ia.jumpedia

        community = jumpedia.create_community(community_name, initial_list_name)

        return ia.dc.followup.send(
            message.layout(
                "Community Created",
                t"The community {community.name:,} was successfully created and is now connected to this server!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Delete a community.")
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    @command.adapt()
    async def nuke(self, ia: InteractionAdapter) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)

        return await confirm.confirm_nuke(
            ia,
            community._o,
            lambda: community.jumpedia.delete_community(community.name),
        )

    @acmds.command(description="Connect a community to this server.")
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    @command.adapt()
    async def connect(
        self, ia: InteractionAdapter, community_name: str
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = ia.jumpedia.add_community_to_current_server(community_name)

        return ia.dc.followup.send(
            message.layout(
                "Community Connected",
                t"This server has successfully been connected to the community {community.name:,}!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Disconnect a community from this server.")
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    @command.adapt()
    async def disconnect(
        self, ia: InteractionAdapter
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = ia.jumpedia.remove_community_from_current_server()

        return ia.dc.followup.send(
            message.layout(
                "Community Disconnected",
                t"The community {community.name:,} has successfully been disconnected from this server!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Transfer the ownership of a community to another user.")
    @acmds.check(predicate.rank_required(CommunityRank.OWNER))
    @command.adapt(rank_to_specify_user=CommunityRank.OWNER)
    async def transfer_ownership(
        self, ia: InteractionAdapter, user: dc.User
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)
        transfer_jumpedia_user = (
            shortcuts.get_or_create_specified_or_current_jumpedia_user(
                community.jumpedia, user
            )
        )

        CONFIG = confirm.ConfirmConfig()

        msg = await ia.dc.followup.send(
            message.layout(
                "Transfer Ownership?",
                t"Are you sure you want to transfer the ownership of {community:,} to {transfer_jumpedia_user:,}?",
                additional=t"This action CANNOT be undone!",
                paragraphs=confirm.get_confirm_paragraphs(CONFIG),
                message_status=message.MessageStatus.WARNING,
            ),
            wait=True,
        )

        if not await confirm.emoji_confirm(ia, msg, config=CONFIG):
            return msg.edit(
                content=message.layout(
                    "Ownership Transfer Aborted",
                    t"The ownership of the community {community:,} stays in your hands, because the request has been aborted!",
                    message.MessageStatus.WARNING,
                )
            )

        return msg.edit(
            content=message.layout(
                "Ownership Transferred",
                t"The ownership of the community {community:,} has successfully been transferred to {transfer_jumpedia_user:,}!",
                additional=t"The rank of {ia.ia_user.name:,} has been set to {CommunityRank.ADMINISTRATOR:,}.",
                message_status=message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Set the default selected list of the community.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt()
    async def set_default_selected_list(
        self, ia: InteractionAdapter, list: str | None = None
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
    @acmds.command(description="Browse all communities.")
    @command.adapt()
    async def browse(
        self, ia: InteractionAdapter
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        communities = ia.jumpedia.get_communities()

        # TODO Make more efficient for more communities

        return await command.browse(
            ia, Community, tuple(map(_comm_to_row, communities))
        )
