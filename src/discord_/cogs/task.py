import builtins
from string.templatelib import Interpolation, Template

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters._user import UserAdapter
from adapters.interaction import InteractionAdapter
from discord_.utils_ import messaging, shortcuts
from utils.rank import CommunityRank

from ..utils_ import predicate
from ..utils_ import user as user_


class TaskCog(cmds.GroupCog, group_name="task"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Get information about a task.")
    async def info(
        self, interaction: dc.Interaction, task: str, list: str | None = None
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        avm = list_obj.get_task(task).get_attribute_value_mapping(
            shortcuts.get_or_create_specified_or_current_community_user(
                list_obj.community, None
            )
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

    browse_group = acmds.Group(name="browse", description="Browse tasks.")

    @browse_group.command(name="all", description="Browse all tasks.")
    async def browse_all(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        await interaction.response.send_message(
            messaging.layout(
                "All Tasks",
                Template(
                    Interpolation("\n".join(task.name for task in list_obj.get_tasks()))
                ),
                messaging.MessageStatus.INFO,
            )
        )

    @browse_group.command(name="user", description="Browse all tasks of a user.")
    async def browse_user(
        self,
        interaction: dc.Interaction,
        user: str | None = None,
        list: str | None = None,
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        list_obj.get_tasks

    @acmds.command(description="Create a new task.")
    @acmds.check(predicate.rank_required(CommunityRank.HELPER))
    async def create(
        self,
        interaction: dc.Interaction,
        name: str,
        aliases: str | None = None,
        attribute_value_mapping: str | None = None,
        list: str | None = None,
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        task = list_obj.create_task(name, aliases, attribute_value_mapping)

        await interaction.response.send_message(
            messaging.layout(
                "Task Created",
                t"The task `{task.name}` has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Delete an existing task.")
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    async def nuke(
        self, interaction: dc.Interaction, task: str, list: str | None = None
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        list_obj.delete_task(task)

        await interaction.response.send_message(
            messaging.layout(
                "Task Delete",
                t"The task `{task}` has successfully been deleted!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Give a task to a user.")
    async def give(
        self,
        interaction: dc.Interaction,
        task: str,
        user_attribute_value_mapping: str | None = None,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> None:
        user_.validate_allowed_for_others(interaction, user, CommunityRank.MODERATOR)

        community_user = shortcuts.get_or_create_specified_or_current_community_user(
            InteractionAdapter(interaction), user
        )
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            community_user, list
        )

        task_obj = list_obj.give_task_to_user(
            task, community_user, user_attribute_value_mapping
        )

        await interaction.response.send_message(
            messaging.layout(
                "Task Given",
                t"The task `{task_obj.name}` has successfully been given to `{community_user.name}`!",
                messaging.MessageStatus.SUCCESS,
            )
        )
