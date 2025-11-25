import typing as t
from string.templatelib import Template

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._user import ServerUserAdapter
from adapters.interaction import InteractionAdapter
from discord_.utils_ import group
from structures.user import CommunityUser
from utils.rank import CommunityRank

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

        jumpedia_user = jumpedia.get_or_create_jumpedia_user_or_current(
            None if user is None else ServerUserAdapter(user, ia)
        )
        community_user = jumpedia.get_current_community().get_or_create_community_user(
            jumpedia_user
        )

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
    async def set_rank(
        self, interaction: dc.Interaction, user: dc.User, rank: CommunityRank
    ) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia = ia.jumpedia
        community = jumpedia.get_current_community()

        set_community_user = community.get_or_create_community_user(
            jumpedia.get_or_create_jumpedia_user(ServerUserAdapter(user, ia))
        )

        await interaction.response.send_message(
            set_community_user.set_community_rank(
                rank, community.get_or_create_current_community_user()
            )
        )

    @set_group.command(name="selected_list")
    async def set_selected_list(
        self,
        interaction: dc.Interaction,
        list: str | None = None,
        user: dc.User | None = None,
    ) -> None:
        ia = InteractionAdapter(interaction)

        jumpedia = ia.jumpedia
        community = jumpedia.get_current_community()

        set_community_user = community.get_or_create_community_user(
            jumpedia.get_or_create_jumpedia_user_or_current(
                None if user is None else ServerUserAdapter(user, ia)
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

    transfer_group = acmds.Group(name="transfer", description="Transfer something.")

    @transfer_group.command(name="ownership")
    @acmds.check(predicate.rank_required(CommunityRank.OWNER))
    async def transfer_ownership(self, interaction: dc.Interaction, user: dc.User) -> None:
        ia = InteractionAdapter(interaction)
        jumpedia = ia.jumpedia
        community = jumpedia.get_current_community()
        transfer_jumpedia_user = jumpedia.get_or_create_jumpedia_user(ServerUserAdapter(user, ia))

        async def after_submit(interaction: dc.Interaction, success: bool) -> None:
            if success:
                current_community_user = community.get_or_create_current_community_user()
                community.get_or_create_community_user(transfer_jumpedia_user).transfer_ownership(current_community_user)

                await interaction.response.send_message(
                    messaging.layout(
                        f"Ownership Transferred",
                        t"The ownership of the community `{community}` has successfully been transferred to `{transfer_jumpedia_user}`!",
                        message_status=messaging.MessageStatus.SUCCESS,
                        additional=t"The rank of `{current_community_user}` has been set to `{CommunityRank.ADMINISTRATOR}`.",
                    )
                )
            else:
                await interaction.response.send_message(
                    messaging.layout(
                        f"Ownership Transfer Aborted",
                        t"The ownership of the community `{community}` stays in your hands, because the name entered was not the specified user's name (`{transfer_jumpedia_user}`)!",
                        messaging.MessageStatus.WARNING,
                    )
                )

        await interaction.response.send_modal(
            modal.ConfirmByEnteringModal(
                interaction,
                f"Confirm Ownership Transfer",
                f"Enter the other user's name to confirm:",
                lambda s: s == transfer_jumpedia_user.name,
                after_submit,
            )
        )