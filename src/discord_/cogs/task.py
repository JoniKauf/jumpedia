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
        
        avm = list_obj.get_task(task).get_attribute_value_mapping(list_obj.community.get_or_create_current_community_user())

        await interaction.response.send_message(
            messaging.layout(
                "Task Info",
                Template(*(
                    Interpolation(f"({attr.__class__.type_name.title()}) {attr.name}: {builtins.list(v)!r}\n")
                    for attr, v
                    in avm.combined.items()
                )),
                message_status=messaging.MessageStatus.INFO
            )
        )