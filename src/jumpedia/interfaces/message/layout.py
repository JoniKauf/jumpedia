import enum
import string
import typing as t
from dataclasses import dataclass
from string.templatelib import Interpolation, Template, convert

from jumpedia.domain.errors.internal import ProgrammingError
from jumpedia.domain.sentinels.default import DEFAULT
from jumpedia.interfaces.message.formatting import (
    F,
    FormatArgsEmpty,
    FormatArgsTypeName,
)


class Status(enum.StrEnum):
    NONE = ""
    INFO = "information_source"
    SUCCESS = "white_check_mark"
    WARNING = "warning"
    ERROR = "x"


MAX_DISCORD_CODE_UNITS: int = 2000


def utf16_code_units(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def discord_message_too_long(s: str) -> bool:
    return utf16_code_units(s) > MAX_DISCORD_CODE_UNITS


def _parse_interpolation(interpolation: Interpolation[F], header: bool) -> str:
    if interpolation.format_spec or interpolation.conversion:
        raise ProgrammingError(f"Format or conversion not allowed! {interpolation!r}")

    f = interpolation.value

    if not isinstance(f, F):
        raise ProgrammingError(
            f"All interpolations' values must be of type {F.__qualname__}, which {f!r} isn't!"
        )

    s = f._s
    args = f._format_args

    del f, interpolation

    if isinstance(args, FormatArgsTypeName):
        capitalize = header if args.capitalize is DEFAULT else args.capitalize

        if capitalize:
            s = string.capwords(s)
    elif isinstance(args, FormatArgsEmpty):
        pass
    else:
        t.assert_never(args)

    return s


def _parse_template(t: Template, header: bool) -> str:
    res: list[str] = []

    for elem in t:
        match elem:
            case str():
                res.append(elem)

            case Interpolation():
                res.append(_parse_interpolation(elem, header))

    return "".join(res)


def layout(header: Template, body: Template, status: Status) -> str:
    header_s = _parse_template(header, True)
    body_s = _parse_template(body, False)
    status_s = (
        "" if status is Status.NONE else f"-# :{status.value}:  {status.name.title()}"
    )

    return f"## {header_s}\n{body_s}\n\n{status_s}".rstrip()
