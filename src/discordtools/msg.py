from dataclasses import dataclass
from enum import Enum
import textwrap
from typing import (Any, Awaitable, Callable, ClassVar, Coroutine, Iterable, Literal, NamedTuple, Sequence,
                    TypedDict)

import discord as dc
from discord.ui import Button, View
import inspect

from discordtools import errors

InteractionFuncT = Callable[..., Coroutine]


# --- Text editing ---

def default_empty() -> str:
    return "<Empty>"

def shorten(s: str, max: int = 32, more: str = '...') -> str:
    return s[:max - len(more)] + more if len(s) > max else s

def shorten_seq(elems: Sequence[str], *, max_elems: int = 8, max_s: int = 16, more_elems: str = '...', more_s: str = '...') -> tuple[str, ...]:
    return (*(shorten(elem, max_s, more_s) for elem in elems[:max_elems]), more_elems) if len(elems) > max_elems else tuple(elems)

def embed_seq(elems: Sequence[str], *, when_empty: str = default_empty()) -> str:
    return f"`{'`, `'.join(elems)}`" if elems else when_empty

def shorten_and_embed_seq(
    elems: Sequence[str], 
    *,
    max_elems: int = 8, 
    max_s: int = 16,
    more_elems: str = '...', 
    more_s: str = '...',
    when_empty: str = default_empty()
):
    return embed_seq(shorten_seq(elems, max_elems=max_elems, max_s=max_s, more_elems=more_elems, more_s=more_s), when_empty=when_empty)



def _get_relevant_kwargs(kwargs: dict[str, Any], func: Callable) -> dict[str, Any]:
    """Get all kwargs a given function accepts."""
    sig = inspect.signature(func)
    return {k: v for k, v in kwargs.items() if k in sig.parameters}


def _is_followup_func(func: InteractionFuncT, interaction: dc.Interaction):
    return func not in (
        interaction.response.send_message,
        interaction.response.edit_message,
        interaction.response.send_modal,
        interaction.response.pong
    )


async def _handle_interaction_func(
    interaction: dc.Interaction,
    msg_kwargs: dict[str, Any] | None = None,
    *,
    success_func: InteractionFuncT | None = None
):
    if success_func is None:
        if interaction.response.is_done():
            success_func = interaction.followup.send
        else:
            success_func = interaction.response.send_message

    else:
        if interaction.response.is_done():
            if _is_followup_func(success_func, interaction):
                await interaction.response.defer()
            else:
                raise ValueError(f"func '{success_func}' not executable anymore, because response is done")
            
    msg_kwargs = _get_relevant_kwargs(msg_kwargs, success_func) if msg_kwargs else {}

    await success_func(**msg_kwargs)

    

@dataclass(frozen=True, slots=True)
class MsgFeedback:
    _init_done: ClassVar[bool] = False

    emoji: str
    name: str

    def __post_init__(self) -> None:
        if self.__class__._init_done:
            raise errors.ProgrammingError()
        
    @classmethod
    def _init(cls) -> None:
        cls.NONE = cls("", "")
        cls.INFO = cls("information_source", "Info")
        cls.SUCCESS = cls("white_check_mark", "Success")
        cls.WARNING = cls("warning", "Warning")
        cls.FAILED = cls("x", "Failed")

        cls._init_done = True

MsgFeedback._init()


def layout(header: str, description: str, message_type: MsgFeedback) -> str:
    result: list[str] = []

    result.append(f"## {header.strip()}")
    result.append(description.strip())
    
    if message_type is not MsgFeedback.NONE:
        result.append(f"\n-# :{message_type.emoji}:  {message_type.name}")

    return '\n'.join(result)