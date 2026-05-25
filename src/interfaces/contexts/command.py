from dataclasses import dataclass
import discord

from interfaces.contexts.interacting_user import InteractingUserContext
from services.services import Services

@dataclass(frozen=True)
class CommandContext:
    services: Services
    interaction: discord.Interaction
    interacting_user_context: InteractingUserContext