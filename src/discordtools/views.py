import asyncio
from typing import Callable, Coroutine
import discord as dc
from discord import app_commands as acmds

from discordtools import messagetools

YES_BUTTON_LABEL = "Yes"

class DangerousConfirm(dc.ui.View):
    def __init__(
        self, 
        interaction: dc.Interaction,
        on_yes: Callable[[dc.Interaction], Coroutine[None, None, bool]], 
        on_no: Callable[[dc.Interaction], Coroutine[None, None, bool]]
    ):
        self.interaction = interaction
        self.on_yes = on_yes
        self.on_no = on_no
        super().__init__(timeout=30)

        asyncio.create_task(self.enable_yes_button())

    async def enable_yes_button(self) -> None:
        await asyncio.sleep(5)

        for child in self.children:
            if isinstance(child, dc.ui.Button) and child.label == YES_BUTTON_LABEL:
                child.disabled = False
                break

        await self.interaction.edit_original_response(view=self)

    async def on_timeout(self) -> None:
        await self.interaction.delete_original_response()

    def disable_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, dc.ui.Button):
                child.disabled = True
                
    @dc.ui.button(style=dc.ButtonStyle.danger, label=YES_BUTTON_LABEL, emoji='⚠️', disabled=True)
    async def yes(self, ia: dc.Interaction, button: dc.ui.Button):
        success = await self.on_yes(ia)

        if not success:
            return

        self.disable_buttons()
        await ia.edit_original_response(view=self)
        self.stop()
        
        
    @dc.ui.button(style=dc.ButtonStyle.green, label="No", emoji='❗')
    async def no(self, ia: dc.Interaction, button: dc.ui.Button):
        success = await self.on_no(ia)

        if not success:
            return
        
        self.disable_buttons()
        await ia.edit_original_response(view=self)
        self.stop()
