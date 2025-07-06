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

def is_followup_func(func: InteractionFuncT, interaction: dc.Interaction):
    return func not in (
        interaction.response.send_message,
        interaction.response.edit_message,
        interaction.response.send_modal,
        interaction.response.pong
    )


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




def code(o: Any) -> str:
    return f"`{o}`"

def code_many(objects: Iterable[Any]) -> Generator[str, None, None]:
    return (code(elem) for elem in objects)

def shorten_and_code(o: Any, max: int = 32, more: str = '...') -> str:
    return text.shorten(code(o), max=max, more=more)

def shorten_and_code_many(
    objects: Sequence[Any], 
    *,
    max_elems: int = 8, 
    max_s: int = 16,
    more_elems: str = '...', 
    more_s: str = '...'
):
    return code_many(text.shorten_many(
        objects, 
        max_elems=max_elems, 
        max_s=max_s, 
        more_elems=more_elems, 
        more_s=more_s
    ))

def code_big(o: Any) -> str:
    return f"```{o}```"