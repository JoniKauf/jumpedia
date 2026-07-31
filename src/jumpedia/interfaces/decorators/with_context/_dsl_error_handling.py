import typing as t
from string.templatelib import Template

import discord

from jumpedia.interfaces.dsls.core.errors.eval import (
    AnyEvalErrorT,
    EmptyAfterNonEqualityOperator,
    UnexpectedBinOp,
    UnexpectedNode,
)
from jumpedia.interfaces.dsls.core.errors.lex import (
    AnyLexErrorT,
    InvalidEscape,
    MultilineStringsDisallowed,
    UnknownChar,
    UnterminatedString,
)
from jumpedia.interfaces.dsls.core.errors.parse import (
    AnyParseErrorT,
    DepthLimitSurpassed,
    UnexpectedToken,
)
from jumpedia.interfaces.dsls.core.value_objects import Span
from jumpedia.interfaces.message import formatting, messages
from jumpedia.interfaces.message.formatting import F
from jumpedia.interfaces.message.mentionable import get_name_of_mentionable


def _highlight_error(s: str, span: Span) -> Template:
    # None Token
    if span == Span(-1, -1):
        span = Span(len(s), len(s))

    if span.begin == span.end:
        underline = "|"
    else:
        underline = "^" * (span.end - span.begin)

    slice_start = max(0, span.begin - 8)
    slice_end = min(len(s), span.end + 8)

    view = s[slice_start:slice_end]

    ellipsis_start = "… " if slice_start > 0 else ""
    ellipsis_end = " …" if slice_end < len(s) else ""

    relative_begin = span.begin - slice_start + len(ellipsis_start)

    return Template(
        "\n".join(
            [
                "```",
                f"{ellipsis_start}{view.strip()}{ellipsis_end}",
                f"{' ' * relative_begin}{underline}",
                "```",
            ]
        )
        + "\n"
    )


async def handle_lex_error(interaction: discord.Interaction, e: AnyLexErrorT) -> None:
    match e:
        case InvalidEscape():
            await messages.error(
                interaction,
                t"Invalid Escape Character",
                _highlight_error(e.s, e.span)
                + t"The escaped character {F.string(e.substring[-1])} is not escapable!",
            )

        case MultilineStringsDisallowed():
            await messages.error(
                interaction,
                t"Multiline Strings Disallowed",
                _highlight_error(e.s, e.span)
                + t"Multiline strings are not allowed for this DSL!",
            )

        case UnterminatedString():
            await messages.error(
                interaction,
                t"Unterminated String",
                _highlight_error(e.s, e.span)
                + (
                    t"The string contains an unterminated escape sequence!"
                    if e.unterminated_escape
                    else t"The string was not closed!"
                ),
            )

        case UnknownChar():
            await messages.error(
                interaction,
                t"Unknown Character",
                _highlight_error(e.s, e.span)
                + t"The character {F.string(e.substring)} is generally invalid!\n"
                + t"Maybe try wrapping the expression in 'single quotes' or \"double quotes\"?",
            )

        case _:
            t.assert_never(e)


async def handle_parse_error(
    interaction: discord.Interaction, e: AnyParseErrorT
) -> None:
    match e:
        case UnexpectedToken():
            await messages.error(
                interaction,
                t"Unexpected Token",
                _highlight_error(e.s, e.received.span)
                + t"Expected one of the following token types:"
                + Template(
                    "".join(
                        f"\n- {formatting.embed(get_name_of_mentionable(elem))}"
                        for elem in e.expected
                    )
                )
                + t"\n... but received the {F.full_mention(e.received.type)}!",
            )

        case DepthLimitSurpassed():
            await messages.error(
                interaction,
                t"Maximum Nesting Depth Exceeded",
                _highlight_error(e.s, e.at.span)
                + t"The maximum nesting depth of {F.string(str(e.max_depth))} was surpassed!",
            )

        case _:
            t.assert_never(e)


# TODO:
# With new formattable and mentionable api rework this so it is not hard codes and uses
# internal names!
async def handle_eval_error(interaction: discord.Interaction, e: AnyEvalErrorT) -> None:
    match e:
        case UnexpectedNode():
            await messages.error(
                interaction,
                t"Unexpected Node",
                _highlight_error(e.s, e.received.span)
                + t"Expected one of the following nodes:"
                + Template(
                    "".join(
                        f"\n- {formatting.embed(elem.__name__)}" for elem in e.expected
                    )
                )
                + t"\n... but received {F.string(type(e.received).__name__)}!",
            )

        case UnexpectedBinOp():
            await messages.error(
                interaction,
                t"Unexpected Binary Operator",
                _highlight_error(e.s, e.received.span)
                + t"Expected one of the following binary operators:"
                + Template(
                    "".join(f"\n- {formatting.embed(op.name)}" for op in e.expected)
                )
                + t"\n... but received {F.string(e.received.type.name)}!",
            )

        case EmptyAfterNonEqualityOperator():
            await messages.error(
                interaction,
                t"Missing Expression",
                _highlight_error(e.s, e.received.span)
                + t"The binary operator {F.string(e.received.type.name)} requires an expression after it!",
            )

        case _:
            t.assert_never(e)
