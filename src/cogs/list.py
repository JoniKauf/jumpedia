import builtins
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from typing import Any, Optional as Opt
from discordtools import msg, predicates, required
from discordtools.context import Context
from discordtools import feedbackerrors as fbe
from structures.attribute import AttributeValueTypeEnum
from structures.ranks import CommunityRank
from utils import parsetools

class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about a list.")
    async def info(self, ia: dc.Interaction, list: str | None = None) -> None:
        ctx = Context(ia)

        if list is None:
            list_obj = ctx.selected_list
        else:
            list_obj = required.list(ctx.community.get_list_by_name(list))
        
        info: builtins.list[tuple[str, Any]] = [("Name", list_obj.name)]

        attributes = list_obj.get_attributes_categorized()

        info.append(("Total Attribute Count", sum(len(attrs) for _, attrs in attributes)))

        for attr_type, attrs in attributes:
            info.append((f"{attr_type.ATTRIBUTE_TYPE_NAME} Count", len(attrs)))
        
        info.append(("Task Count", len(list_obj.get_tasks())))

        await ia.response.send_message(msg.layout(
            "List Info",
            '\n'.join(
                f"**{k}:** {v}" for k, v in info
            ),
            msg.MsgFeedback.INFO
        ))


    list_group = acmds.Group(name="list", description="List object of the list.")

    @list_group.command(name="attributes")
    async def list_attributes(self, ia: dc.Interaction) -> None:
        list = Context(ia).selected_list
        
        result: builtins.list[str] = []

        for attr_type, attr_coll in list.get_attributes_categorized():
            result.append(
                f"__**{attr_type.ATTRIBUTE_TYPE_NAME}**__\n" +
                ('\n'.join(f"- {attr.name}" for attr in attr_coll) or "None")
            )

        await ia.response.send_message(msg.layout(
            "All Attributes",
            '\n\n'.join(result),
            msg.MsgFeedback.INFO
        ))
    

    create_group = acmds.Group(name="create", description="Create objects for a list.")

    @create_group.command(name="task_attribute", description="Create a new task attribute.")
    async def create_task_attribute(
        self, 
        ia: dc.Interaction, 
        name: str, 
        aliases: str, 
        value_type: AttributeValueTypeEnum, 
        max_slots: int, 
        unique_slots: bool, 
        unique_value_per_list: bool, 
        collection: str = "[]", 
        list: str | None = None
    ) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        task_attribute = list_obj.create_task_attribute(
            bad_name=name,
            bad_aliases=parsetools.json_loads_safe(aliases, 1),
            value_type=value_type.value,
            bad_collection=collection,
            max_slots=max_slots,
            unique_slots=unique_slots,
            unique_value_per_list=unique_value_per_list
        )

        await ia.response.send_message(msg.layout(
            "Task Attribute Created",
            f"The task attribute `{task_attribute.name}` has been created successfully!",
            msg.MsgFeedback.SUCCESS
        ))

    
    @create_group.command(name="user_attribute", description="Create a new user attribute.")
    async def create_user_attribute(
        self, 
        ia: dc.Interaction, 
        name: str, 
        aliases: str, 
        value_type: AttributeValueTypeEnum, 
        max_slots: int, 
        unique_slots: bool, 
        collection: str = "[]", 
        list: str | None = None
    ) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        task_attribute = list_obj.create_user_attribute(
            bad_name=name,
            bad_aliases=parsetools.json_loads_safe(aliases, 1),
            value_type=value_type.value,
            bad_collection=collection,
            max_slots=max_slots,
            unique_slots=unique_slots
        )

        await ia.response.send_message(msg.layout(
            "User Attribute Created",
            f"The user attribute `{task_attribute.name}` has been created successfully!",
            msg.MsgFeedback.SUCCESS
        ))
    

    delete_group = acmds.Group(name="delete", description="Delete objects from a list.")

    @delete_group.command(name="task_attribute")
    async def delete_task_attribute(self, ia: dc.Interaction, name: str, list: str | None = None) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                list_obj.delete_task_attribute(name)

                return await ia.response.send_message(msg.layout(
                    "Task Attribute Deleted",
                    f"The task attribute `{list.name}` has successfully been deleted!",
                    msg.MsgFeedback.SUCCESS
                ))

            await ia.response.send_message(msg.layout(
                "List Deletion Aborted",
                f"The list `{list.name}` has **not** been deleted because the name entered is not correct!",
                msg.MsgFeedback.WARNING
            ))

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            ia,
            "Confirm List Deletion",
            "Re-Enter the list's name to confirm",
            lambda s: s == list.name,
            after_submit
        ))



async def setup(bot: cmds.Bot):
    await bot.add_cog(ListCog(bot))