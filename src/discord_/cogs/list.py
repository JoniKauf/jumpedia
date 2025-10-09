import builtins
from typing import Any

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from ..structs import modals
from ..utils import messaging
from ...structures.attribute.slot_type import SlotTypeEnum
from ...structures.attribute.task_attribute import TaskAttribute
from ...structures.attribute.user_attribute import UserAttribute
from ...structures.task import Task
from ...utils import parsetools


class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about a list.")
    async def info(self, ia: dc.Interaction, list: str | None = None) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        info: builtins.list[tuple[str, Any]] = [("Name", list_obj.name)]

        attributes = list_obj.get_attributes_categorized()

        info.append(
            ("Total Attribute Count", sum(len(attrs) for _, attrs in attributes))
        )

        for attr_type, attrs in attributes:
            info.append(
                (f"{attr_type.ATTRIBUTE_TYPE_NAME.title()} Attribute Count", len(attrs))
            )

        info.append(("Task Count", len(list_obj.get_tasks())))

        await ia.response.send_message(
            messaging.layout(
                "List Info",
                "\n".join(f"**{k}:** {v}" for k, v in info),
                messaging.MessageStatus.INFO,
            )
        )

    get_group = acmds.Group(name="get", description="Get objects of the list.")

    @get_group.command(name="attributes", description="Get all attributes of a list.")
    async def get_attributes(self, ia: dc.Interaction, list: str | None = None) -> None:
        list_obj = Context(ia).get_requested_list(list)

        result: builtins.list[str] = []

        for attr_type, attr_coll in list_obj.get_attributes_categorized():
            result.append(
                f"__**{attr_type.ATTRIBUTE_TYPE_NAME.title()}**__\n"
                + ("\n".join(f"- {attr.name}" for attr in attr_coll) or "None")
            )

        await ia.response.send_message(
            messaging.layout(
                "All Attributes", "\n\n".join(result), messaging.MessageStatus.INFO
            )
        )

    @get_group.command(name="tasks", description="Get all tasks of a list.")
    async def get_tasks(self, ia: dc.Interaction, list: str | None = None) -> None:
        list_obj = Context(ia).get_requested_list(list)

        await ia.response.send_message(
            messaging.layout(
                "All Attributes",
                "\n".join(task.name for task in list_obj.get_tasks()),
                messaging.MessageStatus.INFO,
            )
        )

    create_group = acmds.Group(name="create", description="Create objects for a list.")

    @create_group.command(
        name="task_attribute", description="Create a new task attribute."
    )
    async def create_task_attribute(
        self,
        ia: dc.Interaction,
        name: str,
        value_type: SlotTypeEnum,
        max_slots: int,
        unique_slots: bool,
        unique_value_per_list: bool,
        aliases: str = parsetools.EMPTY_JSON_LIST,
        collection: str = parsetools.EMPTY_JSON_LIST,
        list: str | None = None,
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
            unique_value_per_list=unique_value_per_list,
        )

        await ia.response.send_message(
            messaging.layout(
                "Task Attribute Created",
                f"The task attribute `{task_attribute.name}` has been created successfully!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @create_group.command(
        name="user_attribute", description="Create a new user attribute."
    )
    async def create_user_attribute(
        self,
        ia: dc.Interaction,
        name: str,
        value_type: SlotTypeEnum,
        max_slots: int,
        unique_slots: bool,
        aliases: str = parsetools.EMPTY_JSON_LIST,
        collection: str = parsetools.EMPTY_JSON_LIST,
        list: str | None = None,
    ) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        task_attribute = list_obj.create_user_attribute(
            bad_name=name,
            bad_aliases=parsetools.json_loads_safe(aliases, 1),
            value_type=value_type.value,
            bad_collection=collection,
            max_slots=max_slots,
            unique_slots=unique_slots,
        )

        await ia.response.send_message(
            messaging.layout(
                "User Attribute Created",
                f"The user attribute `{task_attribute.name}` has been created successfully!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @create_group.command(
        name="task", description="Create a new task for the specified list."
    )
    async def create_task(
        self,
        ia: dc.Interaction,
        name: str,
        attribute_value_mapping: str = parsetools.EMPTY_JSON_OBJ,
        aliases: str = parsetools.EMPTY_JSON_LIST,
        list: str | None = None,
    ) -> None:
        ctx = Context(ia)
        list_obj = ctx.get_requested_list(list)

        task = list_obj.create_task(name, aliases, attribute_value_mapping)

        await ia.response.send_message(
            messaging.layout(
                "Task Created",
                f"The task `{task.name}` has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    delete_group = acmds.Group(name="delete", description="Delete objects from a list.")

    @delete_group.command(name="task_attribute")
    async def delete_task_attribute(
        self, ia: dc.Interaction, name: str, list: str | None = None
    ) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        task_attribute = required.obj_generic(
            list_obj.get_user_attribute_by_name(name), TaskAttribute
        )

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                list_obj.delete_task_attribute(name)

                return await ia.response.send_message(
                    messaging.layout(
                        "Task Attribute Deleted",
                        f"The task attribute `{task_attribute.name}` has successfully been deleted!",
                        messaging.MessageStatus.SUCCESS,
                    )
                )

            await ia.response.send_message(
                messaging.layout(
                    "Task Attribute Deletion Aborted",
                    f"The task attribute `{task_attribute.name}` has **not** been deleted because the name entered is not correct!",
                    messaging.MessageStatus.WARNING,
                )
            )

        await ia.response.send_modal(
            modals.ConfirmByEnteringModal(
                ia,
                "Confirm Task Attribute Deletion",
                "Re-Enter the task attribute's name to confirm",
                lambda s: s == task_attribute.name,
                after_submit,
            )
        )

    @delete_group.command(name="user_attribute")
    async def delete_user_attribute(
        self, ia: dc.Interaction, name: str, list: str | None = None
    ) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        user_attribute = required.obj_generic(
            list_obj.get_user_attribute_by_name(name), UserAttribute
        )

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                list_obj.delete_user_attribute(name)

                return await ia.response.send_message(
                    messaging.layout(
                        "User Attribute Deleted",
                        f"The task attribute `{user_attribute.name}` has successfully been deleted!",
                        messaging.MessageStatus.SUCCESS,
                    )
                )

            await ia.response.send_message(
                messaging.layout(
                    "User Attribute Deletion Aborted",
                    f"The user attribute `{user_attribute.name}` has **not** been deleted because the name entered is not correct!",
                    messaging.MessageStatus.WARNING,
                )
            )

        await ia.response.send_modal(
            modals.ConfirmByEnteringModal(
                ia,
                "Confirm User Attribute Deletion",
                "Re-Enter the user attribute's name to confirm",
                lambda s: s == user_attribute.name,
                after_submit,
            )
        )

    @delete_group.command(name="task")
    async def delete_task(
        self, ia: dc.Interaction, name: str, list: str | None = None
    ) -> None:
        ctx = Context(ia)

        list_obj = ctx.get_requested_list(list)

        task = required.obj_generic(list_obj.get_task_by_name(name), Task)

        async def after_submit(ia: dc.Interaction, success: bool) -> None:
            if success:
                list_obj.delete_task(name)

                return await ia.response.send_message(
                    messaging.layout(
                        "Task Deleted",
                        f"The task `{task.name}` has successfully been deleted!",
                        messaging.MessageStatus.SUCCESS,
                    )
                )

            await ia.response.send_message(
                messaging.layout(
                    "Task Deletion Aborted",
                    f"The task `{task.name}` has **not** been deleted because the name entered is not correct!",
                    messaging.MessageStatus.WARNING,
                )
            )

        await ia.response.send_modal(
            modals.ConfirmByEnteringModal(
                ia,
                "Confirm User Task Deletion",
                "Re-Enter the task's name to confirm",
                lambda s: s == task.name,
                after_submit,
            )
        )
