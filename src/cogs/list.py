import builtins
import json
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from typing import Any, Optional as Opt
from discordtools import modals, msg, predicates, required
from discordtools.context import Context
from discordtools import feedbackerrors as fbe
from structures.attribute import AttributeValueTypeEnum, StaticAttribute, TaskAttribute, UserAttribute
from structures.jumpedia import Jumpedia
from structures.list import List
from structures.ranks import CommunityRank
from utils import parsetools

class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about a list.")
    async def info(self, ia: dc.Interaction, list: str | None = None) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)
        
        info: builtins.list[tuple[str, Any]] = [("Name", list_obj.name)]

        attributes = list_obj.get_attributes_categorized()

        info.append(("Total Attribute Count", sum(len(attrs) for _, attrs in attributes)))

        for attr_type, attrs in attributes:
            info.append((f"{attr_type.ATTRIBUTE_TYPE_NAME.title()} Attribute Count", len(attrs)))
        
        info.append(("Task Count", len(list_obj.get_tasks())))

        await ia.response.send_message(msg.layout(
            "List Info",
            '\n'.join(
                f"**{k}:** {v}" for k, v in info
            ),
            msg.MsgFeedback.INFO
        ))


    get_group = acmds.Group(name="get", description="Get objects of the list.")

    @get_group.command(name="attributes", description="Get all attributes of a list.")
    async def list_attributes(self, ia: dc.Interaction) -> None:
        list = Context(ia).selected_list
        
        result: builtins.list[str] = []

        for attr_type, attr_coll in list.get_attributes_categorized():
            result.append(
                f"__**{attr_type.ATTRIBUTE_TYPE_NAME.title()}**__\n" +
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
        value_type: AttributeValueTypeEnum, 
        max_slots: int, 
        unique_slots: bool, 
        unique_value_per_list: bool, 
        aliases: str = parsetools.EMPTY_JSON_LIST, 
        collection: str = parsetools.EMPTY_JSON_LIST, 
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
        value_type: AttributeValueTypeEnum, 
        max_slots: int, 
        unique_slots: bool, 
        aliases: str = parsetools.EMPTY_JSON_LIST, 
        collection: str = parsetools.EMPTY_JSON_LIST, 
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
    

    @create_group.command(name="task", description="Create a new task for the specified list.")
    async def create_task(self, ia: dc.Interaction, attribute_value_mapping: str, list: str | None = None) -> None:
        ctx = Context(ia)
        list_obj = ctx.get_requested_list(list)

        attr_values_loaded: dict[str, builtins.list[str]] = parsetools.json_loads_safe(attribute_value_mapping, 2)

        if not isinstance(attr_values_loaded, dict):
            raise fbe.TemporaryFeedbackError("attribute_value_mapping is not a dictionary")
        
        attr_values: dict[StaticAttribute | TaskAttribute, builtins.list[str]] = {}

        for k, v in attr_values_loaded.items():
            if not isinstance(k, str):
                raise fbe.TemporaryFeedbackError(f"Key `{k}` is not a string")
            
            attr = required.obj_generic(
                list_obj.get_task_attribute_by_syn(k) or list_obj.get_static_attribute_by_syn(k), 
                (StaticAttribute, TaskAttribute)
            )

            dumped_v: str = json.dumps(v)

            attr_values[attr] = attr.from_str(dumped_v)

        all_attrs_needed = list_obj.get_static_attributes() + list_obj.get_task_attributes()
        all_attrs_needed = tuple(attr for attr in all_attrs_needed if attr.required)

        for attr in all_attrs_needed:
            if attr not in attr_values:
                raise fbe.TemporaryFeedbackError(f"Required attribute `{attr}` missing!")
            
        

    
    delete_group = acmds.Group(name="delete", description="Delete objects from a list.")

    @delete_group.command(name="task_attribute")
    async def delete_task_attribute(self, ia: dc.Interaction, name: str, list: str | None = None) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        task_attribute = required.obj_generic(list_obj.get_user_attribute_by_name(name), TaskAttribute)

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                list_obj.delete_task_attribute(name)

                return await ia.response.send_message(msg.layout(
                    "Task Attribute Deleted",
                    f"The task attribute `{task_attribute.name}` has successfully been deleted!",
                    msg.MsgFeedback.SUCCESS
                ))

            await ia.response.send_message(msg.layout(
                "Task Attribute Deletion Aborted",
                f"The task attribute `{task_attribute.name}` has **not** been deleted because the name entered is not correct!",
                msg.MsgFeedback.WARNING
            ))

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            ia,
            "Confirm Task Attribute Deletion",
            "Re-Enter the task attribute's name to confirm",
            lambda s: s == task_attribute.name,
            after_submit
        ))

    
    @delete_group.command(name="user_attribute")
    async def delete_user_attribute(self, ia: dc.Interaction, name: str, list: str | None = None) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        user_attribute = required.obj_generic(list_obj.get_user_attribute_by_name(name), UserAttribute)

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                list_obj.delete_user_attribute(name)

                return await ia.response.send_message(msg.layout(
                    "User Attribute Deleted",
                    f"The task attribute `{user_attribute.name}` has successfully been deleted!",
                    msg.MsgFeedback.SUCCESS
                ))

            await ia.response.send_message(msg.layout(
                "User Attribute Deletion Aborted",
                f"The user attribute `{user_attribute.name}` has **not** been deleted because the name entered is not correct!",
                msg.MsgFeedback.WARNING
            ))

        await ia.response.send_modal(modals.ConfirmByEnteringModal(
            ia,
            "Confirm User Attribute Deletion",
            "Re-Enter the user attribute's name to confirm",
            lambda s: s == user_attribute.name,
            after_submit
        ))

    




async def setup(bot: cmds.Bot):
    await bot.add_cog(ListCog(bot))