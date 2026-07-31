import typing as t
from dataclasses import dataclass
from string import Template

from domain.sentinels.default import DEFAULT
from interfaces.message.formattable import FormattableForms, FormattableT
from interfaces.message.mentionable import (
    MentionableT,
    get_name_of_mentionable,
    mentionable_to_formattable,
)


def shorten(s: str, max: int = 32, ellipsis: str = "...") -> str:
    if len(ellipsis) > max:
        raise ValueError("'ellipsis' does not fit into max")

    if len(s) <= max:
        return s

    return s[: max - len(ellipsis)] + ellipsis


def embed(s: str) -> str:
    if not s:
        return "`` ``"

    if s.startswith("`") or s.endswith("`"):
        return f"`` {s} ``"

    return f"``{s}``"


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
    def raw(cls, s: str) -> t.Self:
        return cls(_s=s, _format_args=FormatArgsEmpty())

    @classmethod
    def string(cls, s: str, *, short: bool = True, embedded: bool = True) -> t.Self:
        """Interpolate any string."""

        if short:
            s = shorten(s)

        if embedded:
            s = embed(s)

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
        """Interpolate a formattable object into its valid representation."""

        s = FormattableForms.from_formattable(formattable).case_from_bools(
            plural, possessive
        )

        return cls(_s=s, _format_args=FormatArgsTypeName(capitalize))

    @classmethod
    def min_mention(
        cls, mentionable: MentionableT, *, short: bool = True, embedded: bool = True
    ) -> t.Self:
        s = get_name_of_mentionable(mentionable)

        if short:
            s = shorten(s)

        if embedded:
            s = embed(s)

        return cls(_s=s, _format_args=FormatArgsEmpty())

    @classmethod
    def full_mention(cls, mentionable: MentionableT, *, short: bool = True) -> t.Self:
        """Mention a mentionable object.

        For example, for a list this would be
        <code>List &#96&#96&lt;list name&gt;&#96&#96</code>
        """

        formattable_str = FormattableForms.from_formattable(
            mentionable_to_formattable(mentionable)
        ).singular

        s = f"{formattable_str} {cls.min_mention(mentionable, short=short, embedded=True)._s}"

        return cls(_s=s, _format_args=FormatArgsEmpty())
