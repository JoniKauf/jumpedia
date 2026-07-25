import typing as t
from dataclasses import dataclass

from domain.enums.concept import Concept
from domain.sentinels.default import DEFAULT
from interfaces.message.formattable import FormattableForms, FormattableT
from interfaces.message.mentionable import (
    MentionableT,
    get_name_of_mentionable,
    mentionable_to_formattable,
)


def _shorten(s: str, max: int = 32, ellipsis: str = "...") -> str:
    if len(ellipsis) > max:
        raise ValueError()

    if len(s) <= max:
        return s

    return s[: max - len(ellipsis)] + ellipsis


type FormatArgsT = FormatArgsEmpty | FormatArgsTypeName


@dataclass(frozen=True, slots=True)
class FormatArgsEmpty:
    pass


@dataclass(frozen=True, slots=True)
class FormatArgsTypeName:
    capitalize: bool | DEFAULT


@dataclass(frozen=True, kw_only=True, slots=True)
class F:
    """Class to be used inside interpolations of templates (t-strings) to format
    objects nicely and consistently for actual user display.

    Use its classmethods to generate instances of itself inside of interpolations of
    templates (t-strings).
    """

    _s: str
    _format_args: FormatArgsT

    @classmethod
    def mention(cls, mentionable: MentionableT, *, shorten: bool = True) -> t.Self:
        formattable_str = FormattableForms.from_formattable(
            mentionable_to_formattable(mentionable)
        ).singular
        mentionable_str = get_name_of_mentionable(mentionable)

        if shorten:
            mentionable_str = _shorten(mentionable_str)

        s = f"{formattable_str} ``{mentionable_str}``"

        return cls(_s=s, _format_args=FormatArgsEmpty())

    @classmethod
    def format(
        cls,
        formattable: FormattableT,
        *,
        capitalize: bool | DEFAULT = DEFAULT,
        plural: bool = False,
        possessive: bool = False,
    ) -> t.Self:
        s = FormattableForms.from_formattable(formattable).case_from_bools(
            plural, possessive
        )

        return cls(_s=s, _format_args=FormatArgsTypeName(capitalize))

    @classmethod
    def raw(cls, s: str, *, embed: bool = False) -> t.Self:
        if embed:
            s = f"``{s}``"

        return cls(_s=s, _format_args=FormatArgsEmpty())
