import discord as dc
import discord.ext.commands as cmds
from discord import app_commands as acmds

from discord_.cogs import static_attribute
from structures.attribute import TaskAttribute
from utils.rank import CommunityRank

from ..utils_ import predicate


class TaskttributeCog(cmds.GroupCog, group_name="task_attribute"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Get information about a task attribute.")
    async def info(
        self, interaction: dc.Interaction, task_attribute: str, list: str | None = None
    ) -> None:
        await static_attribute.info(interaction, TaskAttribute, task_attribute, list)

    @acmds.command(description="Browse all task attributes.")
    async def browse(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> None:
        await static_attribute.browse(interaction, TaskAttribute, list)

    @acmds.command(description="Create a new task attribute.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def create(
        self,
        interaction: dc.Interaction,
        name: str,
        slot_type: static_attribute.SlotTypeEnum,
        max_slots: int,
        aliases: str | None = None,
        collection: str | None = None,
        list: str | None = None,
    ) -> None:
        await static_attribute.create(
            interaction,
            TaskAttribute,
            name,
            slot_type,
            max_slots,
            aliases,
            collection,
            list,
        )

    @acmds.command(description="Delete an existing task attribute.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    async def delete(
        self, interaction: dc.Interaction, task_attribute: str, list: str | None = None
    ) -> None:
        await static_attribute.delete(interaction, TaskAttribute, task_attribute, list)
