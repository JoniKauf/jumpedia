import itertools
from string.templatelib import Interpolation, Template
import typing as t
from dataclasses import dataclass

import discord as dc

from .. import errors
from ...utils import text

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
        cls.FAILED = cls("x", "Failed")

        cls._init_done = True


MessageStatus._init()

@dataclass(frozen=True, slots=True)
class Persistent():
    obj: object

def _template_to_data(t: Template) -> list[tuple[str, bool]]:
    result: list[tuple[str, bool]] = []

    for obj in t:
        if isinstance(obj, str):
            result.append((obj, False))
            continue
        
        v = text.apply_f_to_interpolation_value(obj.value, obj.conversion, obj.format_spec)

        if isinstance(obj.value, Persistent):
            result.append((v, False))
        
        result.append((v, True))

    return result

def _get_byte_length(s: str) -> int:
    return len(s.encode('utf-8'))

def layout(
    header: str,
    core: Template,
    message_status: MessageStatus,
    *,
    additional: Template | None = None,
    paragraphs: t.Sequence[Template] = (),
) -> str:
    data: list[list[tuple[str, bool]]] = [
        core_data := _template_to_data(core),
        additional_data := _template_to_data(additional or Template()),
        *(paragraphs_data := list(map(_template_to_data, paragraphs)))
    ]

    header = f"## {header.strip()}\n"

    if message_status is not MessageStatus.NONE:
        message_status_txt = f"\n\n-# :{message_status.emoji}:  {message_status.name}"
    else:
        message_status_txt = ""

    MORE = '...'
    MIN_LENGTH = 5
    MIN_LENGTH_WITH_MORE = len(MORE) + MIN_LENGTH

    while True:
        result: list[str] = [
            header,
            ''.join(e[0] for e in core_data).strip()
        ]

        if additional is not None:
            result.append('\n' + ''.join(e[0] for e in additional_data or ()).strip())

        if paragraphs:
            result.append(''.join(f"\n\n{''.join(e[0] for e in p).strip()}" for p in paragraphs_data))

        result.append(message_status_txt)

        s = ''.join(result)

        if _get_byte_length(s) <= dc.message.utils.DEFAULT_FILE_SIZE_LIMIT_BYTES:
            break

        biggest_i: int = -1
        biggest_j: int = -1
        biggest_length: int = -1

        for i, lst in enumerate(data):
            for j, (s, shortable) in enumerate(lst):
                if not shortable or len(s) <= MIN_LENGTH_WITH_MORE:
                    continue
                
                length = _get_byte_length(s)

                if length > biggest_length:
                    biggest_i, biggest_j, biggest_length = i, j, length

        
        if biggest_length < 0 or len(data[biggest_i][biggest_j][0]) <= MIN_LENGTH_WITH_MORE:
            raise ValueError("String not shortable enough!")
        
        biggest_s = data[biggest_i][biggest_j][0]
        data[biggest_i][biggest_j] = (biggest_s[0:max(MIN_LENGTH, len(biggest_s) / 2)] + MORE, True)

    return ''.join(result)
