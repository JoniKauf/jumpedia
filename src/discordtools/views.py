import discord as dc
from discord import app_commands as acmds
from discord import ui

class AreYouSure(ui.View):
    def __init__(self, *, timeout: float | None = 2):
        super().__init__(timeout=timeout)