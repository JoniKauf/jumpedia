import typing as t
from dataclasses import dataclass
from decimal import Decimal
from string.templatelib import Interpolation, Template
from types import MappingProxyType

import discord as dc
from discord.ext import commands as cmds

from utils import text

if t.TYPE_CHECKING:
    from structures.attribute.slot_str import SlotTypeT

type InteractionFuncT = t.Callable[..., t.Coroutine]


def is_followup_func(func: InteractionFuncT, interaction: dc.Interaction):
    return func not in (
        interaction.response.send_message,
        interaction.response.edit_message,
        interaction.response.send_modal,
        interaction.response.pong,
    )


@dataclass(frozen=True, slots=True)
class MessageStatus:
    _init_done: t.ClassVar[bool] = False

    emoji: str
    name: str

    def __post_init__(self) -> None:
        if self.__class__._init_done:
            raise RuntimeError

    @classmethod
    def _init(cls) -> None:
        cls.NONE = cls("", "")
        cls.INFO = cls("information_source", "Info")
        cls.SUCCESS = cls("white_check_mark", "Success")
        cls.WARNING = cls("warning", "Warning")
        cls.ERROR = cls("x", "Error")

        cls._init_done = True


MessageStatus._init()


class _InterpolationData(t.NamedTuple):
    evaluated: str
    shortable: bool


MAX_DISCORD_CODE_UNITS: int = 2000


def utf16_code_units(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def discord_message_too_long(s: str) -> bool:
    return utf16_code_units(s) > MAX_DISCORD_CODE_UNITS


def embed_join(elem: str, *elems: str) -> str:
    return f"``{"``, ``".join((elem, *elems))}``"


def embed_human_join(elem: str, *elems: str, human_sep: str = "and") -> str:
    elems = (elem, *elems)

    if len(elems) < 2:
        return embed_join(*elems)

    return f"{embed_join(*elems[:-1])} {human_sep} {embed_join(elems[-1])}"


def layout(
    header: str,
    core: Template,
    message_status: MessageStatus,
    *,
    additional: Template | None = None,
    paragraphs: t.Sequence[Template] = (),
) -> str:
    final_templ = (
        Template(
            f"## {header.strip()}\n",
        )
        + core
    )

    if additional is not None:
        final_templ += Template("\n") + additional

    for parag in paragraphs:
        final_templ += Template("\n\n") + parag

    if message_status is not MessageStatus.NONE:
        final_templ += Template(
            f"\n\n-# :{message_status.emoji}:  {message_status.name}"
        )

    interp_to_data: dict[int, _InterpolationData] = {}

    for i, interp in enumerate(final_templ.interpolations):
        if not interp.format_spec:
            interp_to_data[id(interp)] = _InterpolationData(
                text.apply_f_to_interpolation_value(interp) or " ", True
            )

        elif interp.format_spec == "p":
            interp_to_data[id(interp)] = _InterpolationData(str(interp.value), False)

        elif interp.format_spec in (",", "&", "|"):
            format_func: t.Callable[[str, *tuple[str, ...]], str]

            if interp.format_spec == ",":
                format_func = embed_join
            elif interp.format_spec == "&":
                format_func = embed_human_join
            elif interp.format_spec == "|":
                format_func = lambda elem, *elems: embed_human_join(
                    elem, *elems, human_sep="or"
                )
            else:
                t.assert_never(interp.format_spec)

            to_join: t.Iterable[str]

            if isinstance(interp.value, str) or not isinstance(
                interp.value, t.Iterable
            ):
                to_join = (str(interp.value),)
            else:
                to_join = map(str, interp.value)

            interp_to_data[id(interp)] = _InterpolationData(
                format_func(*to_join), False
            )

        else:
            raise ValueError(f"Format Spec of {interp!r} is invalid")

    MIN_LEN: int = 8
    MORE: str = "..."
    MIN_LEN_MINUS_MORE: int = MIN_LEN - len(MORE)

    assert MIN_LEN > 0
    assert MIN_LEN > len(MORE), "MIN_LEN must be bigger than len(MORE)"

    while True:
        s = "".join(
            (
                interp_to_data[id(elem)].evaluated
                if isinstance(elem, Interpolation)
                else elem
            )
            for elem in final_templ
        )

        if not discord_message_too_long(s):
            return s

        biggest: Interpolation | None = None
        biggest_len: int = MIN_LEN

        # Reverse bec we prefer shortening later
        for interp in reversed(final_templ.interpolations):
            evaluated, shortable = interp_to_data[id(interp)]

            if shortable is False:
                continue

            length = len(evaluated)

            if length > biggest_len:
                biggest_len = length
                biggest = interp

        if biggest is None:
            raise ValueError("Layout not shortable enough", s)

        id_ = id(biggest)
        new_length = max(MIN_LEN_MINUS_MORE, biggest_len // 2)
        still_shortable = new_length > MIN_LEN_MINUS_MORE

        interp_to_data[id_] = _InterpolationData(
            interp_to_data[id_].evaluated[:new_length] + MORE,
            still_shortable,
        )


def layout_success(
    header: str,
    core: Template,
    *,
    additional: Template | None = None,
    paragraphs: t.Sequence[Template] = (),
) -> str:
    return layout(
        header,
        core,
        MessageStatus.SUCCESS,
        additional=additional,
        paragraphs=paragraphs,
    )


_SLOT_TYPE_TO_NAME: MappingProxyType[type[SlotTypeT], str] = MappingProxyType(
    {
        bool: "Boolean (true/false)",
        int: "Integer",
        Decimal: "Decimal",
        str: "String (Text)",
    }
)


def slot_type_to_name(slot_type: type[SlotTypeT]) -> str:
    from structures.attribute.slot_str import SLOT_TYPES

    assert _SLOT_TYPE_TO_NAME.keys() == frozenset(SLOT_TYPES)

    return _SLOT_TYPE_TO_NAME[slot_type]
