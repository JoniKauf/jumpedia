from dataclasses import dataclass
from enum import Enum
import textwrap
from typing import (Any, Awaitable, Callable, ClassVar, Coroutine, Generator, Iterable, Iterator, Literal, NamedTuple, Sequence,
                    TypedDict)

import discord as dc
from discord.ui import Button, View
import inspect

import errors
from utils import text

InteractionFuncT = Callable[..., Coroutine]


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
class MessageStatus:
    _init_done: ClassVar[bool] = False

    emoji: str
    name: str

    def __post_init__(self) -> None:
        if self.__class__._init_done:
            raise errors.ImpossibleError()
        
    @classmethod
    def _init(cls) -> None:
        cls.NONE = cls("", "")
        cls.INFO = cls("information_source", "Info")
        cls.SUCCESS = cls("white_check_mark", "Success")
        cls.WARNING = cls("warning", "Warning")
        cls.FAILED = cls("x", "Failed")

        cls._init_done = True

MessageStatus._init()


def layout(header: str, core: str, message_status: MessageStatus, *, additional: str | None = None, paragraphs: Sequence[str] = ()) -> str:
    result: list[str] = []

    result.append(f"## {header.strip()}")
    result.append('\n' + core.strip())

    if additional is not None:
        result.append('\n' + additional.strip())
    
    if paragraphs:
        result.append(''.join(f"\n\n{p}" for p in paragraphs))

    if message_status is not MessageStatus.NONE:
        result.append(f"\n\n-# :{message_status.emoji}:  {message_status.name}")

    return ''.join(result)




def code(s: str) -> str:
    return f"`{s}`"

def code_many(elems: Iterable[str]) -> Generator[str, None, None]:
    return (code(elem) for elem in elems)

def shorten_and_code(s: str, max: int = 32, more: str = '...') -> str:
    return text.shorten(code(s), max=max, more=more)

def shorten_and_code_many(
    elems: Sequence[str], 
    *,
    max_elems: int = 8, 
    max_s: int = 16,
    more_elems: str = '...', 
    more_s: str = '...'
):
    return code_many(text.shorten_many(
        elems, 
        max_elems=max_elems, 
        max_s=max_s, 
        more_elems=more_elems, 
        more_s=more_s
    ))
