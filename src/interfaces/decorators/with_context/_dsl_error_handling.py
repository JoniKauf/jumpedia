

from string.templatelib import Template
import textwrap

import discord

import typing as t

from interfaces.dsls.core.errors.base import AnyDslErrorT
from interfaces.dsls.core.errors.lex import InvalidEscape, MultilineStringsDisallowed, UnknownChar, UnterminatedString
from interfaces.dsls.core.value_objects import Span
from interfaces.message import messages
from interfaces.message.formatting import F


def _highlight_error(s: str, span: Span) -> Template:
    pointer: str
    underline: str = ""

    if span.begin == span.end:
        pointer = "|"
    else:
        pointer = "^"
        underline = "-" * (span.end - span.begin - 1)

    slce = slice(span.begin - 8, min(span.begin + 20, span.end + 8))
    
    return Template(textwrap.dedent(f"""
        ```
        {s[slce]}
        {" " * span.begin}{pointer}{underline}
        ```
    """).strip() + "\n")


async def handle_domain_error(
    interaction: discord.Interaction, e: AnyDslErrorT
) -> None:
    match e:
        case InvalidEscape():
            await messages.error(
                interaction,
                t"Invalid Escape Character",
                _highlight_error(e.s, e.span) + t"The escaped character {F.string(e.substring)} is not escapable!"
            )
        case _: 
            t.assert_never(e)