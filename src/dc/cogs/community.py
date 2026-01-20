import asyncio
import typing as t
from string.templatelib import Template
from types import CoroutineType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapting.interaction import InteractionAdapter
from structures.community import Community
from utils import text
from utils.rank import CommunityRank, JumpediaRank, ServerRank

from dc_utils import command, confirm, message, modal, predicate, shortcuts


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about the community.")
    @command.adapt
    async def info(self, ia: InteractionAdapter) -> CoroutineType[None, None, t.Any]:
        community = shortcuts.get_current_community(ia)

        default_selected_list = community.get_default_selected_list(None)
        default_selected_list_name = (
            default_selected_list.name if default_selected_list is not None else "None"
        )

        return ia.dc.response.send_message(
            message.layout(
                "Community Info",
                text.join_t(
                    "\n",
                    (
                        t"**{k:p}:** {v}"
                        for k, v in [
                            ("Name", community.name),
                            ("Server Count", community.get_server_count()),
                            ("List Count", len(community.get_lists())),
                            ("Default Selected List", default_selected_list_name),
                        ]
                    ),
                ),
                message.MessageStatus.INFO,
            )
        )

    @acmds.command(description="Create a community.")
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    @command.adapt
    async def create(
        self,
        ia: InteractionAdapter,
        community_name: str,
        initial_list_name: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        jumpedia = ia.jumpedia

        community = jumpedia.create_community(community_name, initial_list_name)

        return ia.dc.response.send_message(
            message.layout(
                "Community Created",
                t"The community {community.name:,} was successfully created and is now connected to this server!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Delete a community.")
    @acmds.check(predicate.rank_required(JumpediaRank.META_ADMINISTRATOR))
    @command.adapt
    async def nuke(self, ia: InteractionAdapter) -> CoroutineType[None, None, t.Any]:
        community = shortcuts.get_current_community(ia)

        return confirm.confirm_nuke(ia, community._o)

    @acmds.command(description="Connect a community to this server.")
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    @command.adapt
    async def connect(
        self, ia: InteractionAdapter, community_name: str
    ) -> CoroutineType[None, None, t.Any]:
        community = ia.jumpedia.add_community_to_current_server(community_name)

        return ia.dc.response.send_message(
            message.layout(
                "Community Connected",
                t"This server has successfully been connected to the community {community.name:,}!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Disconnect a community from this server.")
    @acmds.check(predicate.rank_required(ServerRank.OWNER))
    @command.adapt
    async def disconnect(
        self, ia: InteractionAdapter
    ) -> CoroutineType[None, None, t.Any]:
        community = ia.jumpedia.remove_community_from_current_server()

        return ia.dc.response.send_message(
            message.layout(
                "Community Disconnected",
                t"The community {community.name:,} has successfully been disconnected from this server!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Transfer the ownership of a community to another user.")
    @acmds.check(predicate.rank_required(CommunityRank.OWNER))
    @command.adapt
    async def transfer_ownership(
        self, ia: InteractionAdapter, user: dc.User
    ) -> CoroutineType[None, None, t.Any]:
        community = shortcuts.get_current_community(ia)
        transfer_jumpedia_user = (
            shortcuts.get_or_create_specified_or_current_jumpedia_user(
                community.jumpedia, user
            )
        )

        await ia.dc.response.defer()

        CONFIG = confirm.ConfirmConfig()

        msg = await ia.dc.followup.send(
            message.layout(
                "Transfer Ownership?",
                t"Are you sure you want to transfer the ownership of {community:,} to {transfer_jumpedia_user:,}?",
                additional=t"This action CANNOT be undone!",
                paragraphs=confirm.get_confirm_paragraphs(CONFIG),
                message_status=message.MessageStatus.WARNING
            ),
            wait=True
        )

        if confirm.emoji_confirm(ia, msg, config=CONFIG):
            return msg.edit(
                content=message.layout(
                    "Ownership Transferred",
                    t"The ownership of the community {community:,} has successfully been transferred to {transfer_jumpedia_user:,}!",
                    additional=t"The rank of {ia.current_user.name:,} has been set to {CommunityRank.ADMINISTRATOR:,}.",
                    message_status=message.MessageStatus.SUCCESS,
                )
            )

        return msg.edit(
            content=message.layout(
                "Ownership Transfer Aborted",
                t"The ownership of the community {community:,} stays in your hands, because the name entered was not the specified user's name ({transfer_jumpedia_user:,})!",
                message.MessageStatus.WARNING,
            )
        )


    @acmds.command(description="Set the default selected list of the community.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def set_default_selected_list(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> CoroutineType[None, None, t.Any]:
        community = shortcuts.get_current_community(InteractionAdapter(interaction))

        if list is not None:
            selected_list = community.get_list(list).name
        else:
            selected_list = None

        community.set_default_selected_list(selected_list)

        return interaction.response.send_message(
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
    @command.adapt
    async def browse(self, ia: InteractionAdapter) -> CoroutineType[None, None, t.Any]:
        communities = ia.jumpedia.get_communities()

        listing: Template

        if communities:
            listing = text.join_t("\n", (t"- {comm.name:p}" for comm in communities))
        else:
            listing = t"None"

        return ia.dc.response.send_message(
            message.layout(
                "All Communities",
                listing,
                message.MessageStatus.INFO,
            )
        )