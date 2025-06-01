import asyncio
from types import CoroutineType
from typing import Any, Callable
import discord as dc
from discord import ui

from discord import app_commands as acmds
from discord.utils import MISSING


class ConfirmByEnteringModal(ui.Modal):
    def __init__(
        self, 
        label: str,
        confirm_text: str,
        after_submit: Callable[[dc.Interaction, bool], CoroutineType[Any, Any, None]],
        timeout: float
    ) -> None:
        super().__init__(title="Confirm", timeout=timeout)

        self.confirm_text = confirm_text
        self.after_submit = after_submit

        self.text_input = ui.TextInput(label=label, style=dc.TextStyle.short)
        self.add_item(self.text_input)
        self.text_input.placeholder = f"This modal will timeout after {timeout} seconds!"

        self.virtual_timeout = timeout
        asyncio.create_task(self.dispose())

    async def dispose(self):
        await asyncio.sleep(self.virtual_timeout)

        self.stop()

    async def on_submit(self, ia: dc.Interaction) -> None:
        await self.after_submit(ia, self.confirm_text == self.text_input.value)