import builtins
from string.templatelib import Interpolation, Template

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters.interaction import InteractionAdapter
from discord_.utils_ import messaging

from ..utils_ import predicate


class TaskCog(cmds.GroupCog, group_name="task"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def info(
        self, interaction: dc.Interaction, task: str, list: str | None = None
    ) -> None:
        list_obj = (
            InteractionAdapter(interaction)
            .jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_selected_list_or_default(list)
        )

        avm = list_obj.get_task(task).get_attribute_value_mapping(
            list_obj.community.get_or_create_current_community_user()
        )

        elems: list[str | Interpolation] = []

        for attr, v in avm.combined.items():
            elems.append(Interpolation(f"**{attr.name.replace('*', '\\*')}**: "))

            if not v:
                elems.append(str(None))
            else:
                elems.append(f"`{'`, `'.join(v)}`")

            elems.append("\n")

        elems.pop()

        await interaction.response.send_message(
            messaging.layout(
                "Task Info",
                Template(*elems),
                message_status=messaging.MessageStatus.INFO,
            )
        )
