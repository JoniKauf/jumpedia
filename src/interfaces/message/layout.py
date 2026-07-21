import enum
import typing as t
from dataclasses import dataclass
from string.templatelib import Interpolation, Template, convert

from interfaces.message.format import F


class Status(enum.StrEnum):
    NONE = ""
    INFO = "information_source"
    SUCCESS = "white_check_mark"
    WARNING = "warning"
    ERROR = "x"


def _parse_interpolation(interpolation: Interpolation[F]) -> str:
    if interpolation.format_spec or interpolation.conversion:
        raise ValueError("Format or conversion not allowed rn")

    obj = interpolation.value

    if not isinstance(obj, F):
        raise ValueError("Not F wrapped")

    return obj._s


def _parse_template(t: Template) -> str:
    res: list[str] = []

    for elem in t:
        match elem:
            case str():
                res.append(elem)

            case Interpolation():
                res.append(_parse_interpolation(elem))

    return "".join(res)


def layout(header: Template, body: Template, status: Status) -> str:
    sheader = _parse_template(header)
    sbody = _parse_template(body)
    sstatus = (
        "" if status is Status.NONE else f"-# :{status.value}:  {status.name.title()}"
    )

    return f"## {sheader}\n{sbody}\n\n{sstatus}".rstrip()