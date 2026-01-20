import asyncio
from string.templatelib import Template
from types import CoroutineType
import typing as t
import discord as dc

from adapting.interaction import InteractionAdapter
from dc_utils import message, shortcuts
from dc_utils import errors
from dc_utils.errors import FeedbackError
from structures import BaseStructure

TIMEOUT: t.Final[int] = 30

async def wait_for_emoji_of_executer(ia: InteractionAdapter, emoji: str, *emojis: str, timeout: int = TIMEOUT) -> tuple[dc.Reaction, dc.User | dc.Member]:
    def check(reaction: dc.Reaction, user: dc.User | dc.Member) -> bool:
        if user.id != ia.current_user.id:
            return False

        if ia.dc.message is None or ia.dc.message.id != reaction.message.id:
            return False

        return str(reaction.emoji) in (emoji, *emojis)
    
    return await ia.dc.client.wait_for('reaction_add', check=check, timeout=timeout)


async def emoji_confirm(ia: InteractionAdapter, msg: dc.WebhookMessage, *, config: ConfirmConfig) -> bool:
    await msg.add_reaction(config.no)

    if config.wait_until_yes > 0:
        await msg.add_reaction(config.wait)
        await asyncio.sleep(config.wait_until_yes)

        assert ia.dc.client.user is not None

        await msg.remove_reaction(config.wait, ia.dc.client.user)

    await msg.add_reaction(config.yes)

    try:
        reaction, _ = await wait_for_emoji_of_executer(ia, config.yes, config.no, timeout=config.timeout)
    except asyncio.TimeoutError:
        return False
    
    # Check exactly for yes because if the emoji checks somehow fails it should rather not delete
    if str(reaction.emoji) == config.yes:
        return True
    
    return False
  
def get_confirm_paragraphs(config: ConfirmConfig) -> tuple[Template, ...]:
    return (
        t"React with {config.no} to **abort** the deletion!\nReact with {config.yes} to **confirm** the deletion{f' (appears after {config.wait_until_yes} seconds)' if config.wait_until_yes > 0 else '':p}!", 
        t"The request will automatically abort after {config.timeout} seconds!"
    )

class ConfirmConfig(t.NamedTuple):
    yes: str = '✅'
    wait: str = '⚙️'
    no: str = '❌'
    wait_until_yes: int = 0
    timeout: int = TIMEOUT

async def confirm_nuke(ia: InteractionAdapter, structure: BaseStructure) -> CoroutineType[None, None, t.Any]:
    CONFIG = ConfirmConfig('💣', '⚙️', '❌', 5, 30)

    if not ia.dc.response.is_done():
        await ia.dc.response.defer()

    msg = await ia.dc.followup.send(
        message.layout(
            f"Nuke {type(structure).type_name.title()}?",
            t"Are you sure you want to PERMANENTLY delete the {type(structure).type_name.lower()} {structure:,}?",
            additional=t"This will also delete all associated data (including user data) from Jumpedia FOREVER!",
            paragraphs=get_confirm_paragraphs(CONFIG),
            message_status=message.MessageStatus.WARNING
        ),
        wait=True
    )
    
    if not await emoji_confirm(ia, msg, **CONFIG._asdict()):
        raise errors.DeletionAborted(structure)
    
    return msg.edit(
        content=message.layout(
            f"{type(structure).type_name.title()} Nuked",
            t"The {type(structure).type_name.lower()} has successfully been deleted!",
            message_status=message.MessageStatus.SUCCESS
        )
    )
    
