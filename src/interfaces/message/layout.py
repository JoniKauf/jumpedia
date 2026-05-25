from dataclasses import dataclass
import enum
from string.templatelib import Interpolation, Template, convert
from types import UnionType
import typing as t
from interfaces.message import format


class Status(enum.StrEnum):
    NONE = ""
    INFO = "information_source"
    SUCCESS = "white_check_mark"
    WARNING = "warning"
    ERROR = "x"


def _parse_interpolation(interpolation: Interpolation) -> str:
    if interpolation.format_spec:
        raise ValueError("Format is no longer supported")

    obj = interpolation.value

    if not isinstance(obj, _TaggedObj):
        obj = _TaggedObj(obj)

    return str(obj)


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


class T(enum.IntFlag):
    EMBED = 1 << 0
    SHORTEN = 1 << 1

    # combos
    NONE = 0
    FORMATTED = EMBED | SHORTEN
    RAW = NONE
    DEFAULT = FORMATTED

    def __rmatmul__(self, value: t.Any) -> _TaggedObj:
        # overwrite tags
        if isinstance(value, _TaggedObj):
            return _TaggedObj(value.obj, self)

        return _TaggedObj(value, self)

    def has_flag(self, flag: T) -> bool:
        return self & flag == flag


@dataclass(frozen=True, slots=True)
class _TaggedObj:
    obj: t.Any
    flags: T = T.DEFAULT

    def __str__(self) -> str:
        s = str(self.obj)

        if self.flags.has_flag(T.SHORTEN):
            s = format.shorten(s, 32)

        if self.flags.has_flag(T.EMBED):
            s = f"``{s}``"

        return s
