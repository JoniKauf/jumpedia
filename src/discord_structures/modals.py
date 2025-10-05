import asyncio
from types import CoroutineType
from typing import Any, Callable, Coroutine
import discord as dc
from discord import ui

from discord import app_commands as acmds
from discord.utils import MISSING

from discordtools import messaging
from structures import BaseStructure


class ConfirmByEnteringModal(ui.Modal):
    def __init__(
        self,
        interaction: dc.Interaction,
        title: str,
        label: str,
        predicate: Callable[[str], bool],
        after_submit: Callable[[dc.Interaction, bool], Coroutine[Any, Any, None]],
        timeout: float = 180,
    ) -> None:
        super().__init__(title=title, timeout=timeout)

        self.predicate = predicate
        self.after_submit = after_submit

        self.text_input = ui.TextInput(label=label, style=dc.TextStyle.short)
        self.text_input.placeholder = (
            "This action is irreversable and cannot be undone!"
        )
        self.add_item(self.text_input)

        self.virtual_timeout = timeout

        asyncio.create_task(self.info_message(interaction))
        asyncio.create_task(self.dispose())

    async def info_message(self, interaction: dc.Interaction) -> None:
        await interaction.followup.send(
            messaging.layout(
                "Awaiting Confirmation",
                "Please fill out the modal that should be appearing on your screen to confirm!",
                messaging.MessageStatus.INFO,
            ),
            ephemeral=True,
        )

    async def dispose(self):
        await asyncio.sleep(self.virtual_timeout)

        self.stop()

    async def on_submit(self, ia: dc.Interaction) -> None:
        await self.after_submit(ia, self.predicate(self.text_input.value))



async def delete_structure_confirmation(structure: type[BaseStructure], delete: Callable[[dc.Interaction], None]):
    async def after_submit(interaction: dc.Interaction, success: bool) -> None:
        if success:
            delete(interaction)

            await interaction.response.send_message(
                messaging.layout(
                    f"{structure.structure_name.title()} Deleted",
                    f"The speicifed {structure.structure_name} has successfully been deleted!",
                    messaging.MessageStatus.SUCCESS,
                )
            )
            return

        await interaction.response.send_message(
            messaging.layout(
                "List Deletion Aborted",
                f"The list `{list.name}` has **not** been deleted because the name entered is not correct!",
                messaging.MessageStatus.WARNING,
            )
        )

    await interaction.response.send_modal(
        modals.ConfirmByEnteringModal(
            interaction,
            "Confirm List Deletion",
            "Re-Enter the list's name to confirm",
            lambda s: s == list.name,
            after_submit,
        )
    )