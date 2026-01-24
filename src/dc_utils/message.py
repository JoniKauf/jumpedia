import enum
import typing as t
from dataclasses import dataclass
from decimal import Decimal
from string.templatelib import Interpolation, Template
from types import MappingProxyType

from utils import text

if t.TYPE_CHECKING:
    from structures.attribute.slot_str import SlotTypeT


class MessageStatus(enum.StrEnum):
    NONE = ""
    INFO = "information_source"
    SUCCESS = "white_check_mark"
    WARNING = "warning"
    ERROR = "x"


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
            f"\n\n-# :{message_status.value}:  {message_status.name.title()}"
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


_SLOT_TYPE_TO_DATA: MappingProxyType[type[SlotTypeT], tuple[str, Template]] = (
    MappingProxyType(
        {
            bool: ("Boolean (true/false)", t"either be {'true':,} or {'false':,}"),
            int: (
                "Integer",
                t"represent any whole number between -(2^63) and 2^63 - 1",
            ),
            Decimal: (
                "Decimal",
                t"represent any real number between -(2^63) and 2^63 - 1 with preferrably less than or exactly 28 decimal places (all decimals after that are trimmed).",
            ),
            str: (
                "String (Text)",
                t"represent any characters sequence between {1:,} and {255:,} characters (unicode code points) in length",
            ),
        }
    )
)


def slot_type_to_name(slot_type: type[SlotTypeT]) -> str:
    from structures.attribute.slot_str import SLOT_TYPES

    assert _SLOT_TYPE_TO_DATA.keys() == frozenset(SLOT_TYPES)

    return _SLOT_TYPE_TO_DATA[slot_type][0]


def slot_type_to_must(slot_type: type[SlotTypeT]) -> Template:
    from structures.attribute.slot_str import SLOT_TYPES

    assert _SLOT_TYPE_TO_DATA.keys() == frozenset(SLOT_TYPES)

    return _SLOT_TYPE_TO_DATA[slot_type][1]
