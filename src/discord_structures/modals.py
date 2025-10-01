import asyncio
from types import CoroutineType
from typing import Any, Callable, Coroutine
import discord as dc
from discord import ui

from discord import app_commands as acmds
from discord.utils import MISSING

from discordtools import messaging


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
