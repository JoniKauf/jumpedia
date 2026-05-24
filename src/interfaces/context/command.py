from dataclasses import dataclass
from sqlalchemy.orm import Session
import discord

from domain.entities.user import UserEntity
from interfaces.context.interacting_user import InteractingUserContext


@dataclass(frozen=True)
class CommandContext:
    session: Session
    interaction: discord.Interaction
    interacting_user_context: InteractingUserContext
