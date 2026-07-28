import textwrap
import typing as t
from string.templatelib import Template

import discord

from interfaces.dsls.core.errors.base import AnyDslErrorT
from interfaces.dsls.core.errors.lex import InvalidEscape
from interfaces.dsls.core.value_objects import Span
from interfaces.message import messages
from interfaces.message.formatting import F


def _highlight_error(s: str, span: Span) -> Template:
    underline: str = ""

    print(span.end, span.begin, span.end - span.begin, "^" * (span.end - span.begin))
    if span.begin == span.end:
        underline = "|"
    else:
        underline = "^" * (span.end - span.begin)

    slce = slice(
        max(0, span.begin - 8), max(min(span.begin + 20, span.end + 8), len(s))
    )

    opt_ellipsis_start: str = ""
    opt_ellipsis_end: str = ""

    if slce.start > 0:
        opt_ellipsis_start = "… "

    if slce.stop < len(s):
        opt_ellipsis_end = " …"

    return Template(textwrap.dedent(f"""
        ```
        {opt_ellipsis_start}{s[slce]}{opt_ellipsis_end}
        {" " * span.begin}{underline}{underline}
        ```
    """).strip() + "\n")


async def handle_dsl_error(interaction: discord.Interaction, e: AnyDslErrorT) -> None:
    match e:
        case InvalidEscape():
            await messages.error(
                interaction,
                t"Invalid Escape Character",
                _highlight_error(e.s, e.span)
                + t"The escaped character {F.string(e.substring[-1])} is not escapable!",
            )
        case _:
            t.assert_never(e)
