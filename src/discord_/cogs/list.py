import builtins
import enum
from decimal import Decimal
from string.templatelib import Interpolation, Template
from types import MappingProxyType
from typing import Any

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters.interaction import InteractionAdapter
from structures.attribute import ALL_ATTRIBUTE_TYPES, TaskAttribute, UserAttribute
from structures.attribute.slot_str import SLOT_TYPES, SlotTypeT
from structures.task import Task
from utils import text

from ..utils_ import messaging, modals

_SLOT_TYPE_TO_NAME: MappingProxyType[type[SlotTypeT], str] = MappingProxyType(
    {
        bool: "Boolean (true/false)",
        int: "Integer",
        Decimal: "Decimal",
        str: "String (Text)",
    }
)

assert _SLOT_TYPE_TO_NAME.keys() == frozenset(SLOT_TYPES)


class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about a list.")
    async def info(self, interaction: dc.Interaction, list: str | None = None) -> None:
        ia = InteractionAdapter(interaction)

        list_obj = (
            ia.jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_list_or_default(list)
        )

        info: builtins.list[tuple[str, Any]] = [("Name", list_obj.name)]

        attributes = list_obj.get_attributes()

        info.append(("Total Attribute Count", sum(len(type) for type in attributes)))

        for i, type in enumerate(attributes):
            info.append(
                (f"{ALL_ATTRIBUTE_TYPES[i].type_name.title()} Count", len(type))
            )

        info.append(("Task Count", len(list_obj.get_tasks())))

        await interaction.response.send_message(
            messaging.layout(
                "List Info",
                Template("\n".join(f"**{k}:** {v}" for k, v in info)),
                messaging.MessageStatus.INFO,
            )
        )

    get_group = acmds.Group(name="get", description="Get objects of the list.")

    @get_group.command(name="attributes", description="Get all attributes of a list.")
    async def get_attributes(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> None:
        list_obj = (
            InteractionAdapter(interaction)
            .jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_list_or_default(list)
        )

        result: builtins.list[str] = []

        for i, group in enumerate(list_obj.get_attributes()):
            result.append(
                f"__**{ALL_ATTRIBUTE_TYPES[i].type_name.title()}**__\n"
                + ("\n".join(f"- {attr.name}" for attr in group) or "None")
            )

        await interaction.response.send_message(
            messaging.layout(
                "All Attributes",
                text.join_t("\n\n", (Template(Interpolation(part)) for part in result)),
                messaging.MessageStatus.INFO,
            )
        )

    @get_group.command(name="tasks", description="Get all tasks of a list.")
    async def get_tasks(
        self, interaction: dc.Interaction, list: str | None = None
    ) -> None:
        list_obj = (
            InteractionAdapter(interaction)
            .jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_list_or_default(list)
        )

        await interaction.response.send_message(
            messaging.layout(
                "All Attributes",
                Template(
                    Interpolation("\n".join(task.name for task in list_obj.get_tasks()))
                ),
                messaging.MessageStatus.INFO,
            )
        )

    create_group = acmds.Group(name="create", description="Create objects for a list.")

    SlotTypeEnum = enum.Enum(
        "SlotTypeEnum", [(_SLOT_TYPE_TO_NAME[type], type) for type in SLOT_TYPES] + []
    )

    async def _create_attribute(
        self,
        interaction: dc.Interaction,
        type: type[TaskAttribute | UserAttribute],
        name: str,
        slot_type: SlotTypeEnum,
        max_slots: int,
        aliases: str | None,
        collection: str | None,
        list: str | None,
    ) -> None:
        list_obj = (
            InteractionAdapter(interaction)
            .jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_list_or_default(list)
        )

        attr = list_obj.create_attribute(
            type, name, slot_type.value, max_slots, aliases, collection
        )

        await interaction.response.send_message(
            messaging.layout(
                f"{type.type_name.title()} Created",
                t"The {type.type_name.lower()} `{attr.name:p}` has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @create_group.command(
        name="task_attribute", description="Create a new task attribute."
    )
    async def create_task_attribute(
        self,
        interaction: dc.Interaction,
        name: str,
        slot_type: SlotTypeEnum,
        max_slots: int,
        aliases: str | None = None,
        collection: str | None = None,
        list: str | None = None,
    ) -> None:
        await self._create_attribute(
            interaction,
            TaskAttribute,
            name,
            slot_type,
            max_slots,
            aliases,
            collection,
            list,
        )

    @create_group.command(
        name="user_attribute", description="Create a new user attribute."
    )
    async def create_user_attribute(
        self,
        interaction: dc.Interaction,
        name: str,
        slot_type: SlotTypeEnum,
        max_slots: int,
        aliases: str | None = None,
        collection: str | None = None,
        list: str | None = None,
    ) -> None:
        await self._create_attribute(
            interaction,
            UserAttribute,
            name,
            slot_type,
            max_slots,
            aliases,
            collection,
            list,
        )

    @create_group.command(
        name="task", description="Create a new task for the specified list."
    )
    async def create_task(
        self,
        interaction: dc.Interaction,
        name: str,
        aliases: str | None = None,
        attribute_value_mapping: str | None = None,
        list: str | None = None,
    ) -> None:
        ia = InteractionAdapter(interaction)

        list_obj = (
            ia.jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_list_or_default(list)
        )

        task = list_obj.create_task(name, aliases, attribute_value_mapping)

        await interaction.response.send_message(
            messaging.layout(
                "Task Created",
                t"The task `{task.name}` has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    delete_group = acmds.Group(name="delete", description="Delete objects from a list.")

    async def _delete_attribute(
        self,
        interaction: dc.Interaction,
        type: type[TaskAttribute | UserAttribute],
        syn: str,
        list: str | None,
    ) -> None:
        list_obj = (
            InteractionAdapter(interaction)
            .jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_list_or_default(list)
        )

        attr_s = list_obj.get_attribute(type, syn)._s

        await modals.delete_structure_confirmation(
            interaction,
            type,
            attr_s.name,
            lambda _: list_obj._s.delete_attribute(type, attr_s.id),
        )

    @delete_group.command(name="task_attribute")
    async def delete_task_attribute(
        self, interaction: dc.Interaction, task_attribute: str, list: str | None = None
    ) -> None:
        await self._delete_attribute(interaction, TaskAttribute, task_attribute, list)

    @delete_group.command(name="user_attribute")
    async def delete_user_attribute(
        self, interaction: dc.Interaction, user_attribute: str, list: str | None = None
    ) -> None:
        await self._delete_attribute(interaction, UserAttribute, user_attribute, list)

    @delete_group.command(name="task")
    async def delete_task(
        self, interaction: dc.Interaction, task: str, list: str | None = None
    ) -> None:
        list_obj = (
            InteractionAdapter(interaction)
            .jumpedia.get_current_community()
            .get_or_create_current_community_user()
            .get_list_or_default(list)
        )

        list_obj.delete_task(task)
