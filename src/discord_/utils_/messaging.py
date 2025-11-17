import typing as t
from dataclasses import dataclass
from string.templatelib import Interpolation, Template

import discord as dc

from utils import text

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
        if interp.format_spec == "p":
            interp_to_data[id(interp)] = data = _InterpolationData(
                str(interp.value), False
            )
        else:
            interp_to_data[id(interp)] = data = _InterpolationData(
                text.apply_f_to_interpolation_value(interp), True
            )

        prev_str, next_str = final_templ.strings[i], final_templ.strings[i + 1]

        if prev_str.endswith("`") and next_str.startswith("`"):
            interp_to_data[id(interp)] = _InterpolationData(
                data.evaluated.replace("`", "´"), data.shortable
            )

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

        if utf16_code_units(s) <= MAX_DISCORD_CODE_UNITS:
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
            raise ValueError("Layout not shortable enough")

        id_ = id(biggest)
        new_length = max(MIN_LEN_MINUS_MORE, biggest_len // 2)
        still_shortable = new_length > MIN_LEN_MINUS_MORE

        interp_to_data[id_] = _InterpolationData(
            interp_to_data[id_].evaluated[:new_length] + MORE,
            still_shortable,
        )
