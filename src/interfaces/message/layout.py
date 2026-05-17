import enum
from string.templatelib import Interpolation, Template, convert


class Status(enum.StrEnum):
    NONE = ""
    INFO = "information_source"
    SUCCESS = "white_check_mark"
    WARNING = "warning"
    ERROR = "x"


def _parse_interpolation(interpolation: Interpolation) -> str:
    obj = interpolation.value
    embed: bool

    if isinstance(obj, Template):
        obj = _parse_template(obj)
        embed = False
    else:
        embed = True

    for c in interpolation.format_spec:
        # f string like
        if c == "f":
            obj = convert(obj, interpolation.conversion)

        # no embed
        elif c == "#":
            embed = not embed

    if embed:
        return f"``{obj}``"

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
