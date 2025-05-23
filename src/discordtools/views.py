import asyncio
from typing import Callable, Coroutine
import discord as dc
from discord import app_commands as acmds

class DangerousConfirm(dc.ui.View):
    def __init__(self, on_yes: Callable[[dc.Interaction], Coroutine[None, None, bool]]):
        self.on_yes = on_yes
        super().__init__(timeout=30)
    
    def on_timeout(self) -> None:
        self.disable_all_buttons()

    def disable_all_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, dc.ui.Button):
                child.disabled = True
                
    @dc.ui.button(style=dc.ButtonStyle.danger, label="Yes", emoji='⚠️')
    async def yes(self, ia: dc.Interaction, button: dc.ui.Button):
        success = await self.on_yes(ia)

        if success:
            self.disable_all_buttons()
            self.timeout = 3
        
        
    @dc.ui.button(style=dc.ButtonStyle.green, label="No")
    async def cancel(self, ia: dc.Interaction, button: dc.ui.Button):
        self.disable_all_buttons()
        self.timeout = 3
