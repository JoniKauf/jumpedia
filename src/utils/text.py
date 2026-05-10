import typing as t
from string.templatelib import Interpolation, Template, convert

def human_join(
    objects: t.Sequence[t.Any], final_delimiter: str, delimiter: str = ", "
) -> str:
    objects_str = tuple(map(str, objects))

    if len(objects) <= 1:
        return delimiter.join(objects_str)

    return f"{delimiter.join(objects_str[:-1])}{final_delimiter}{objects[-1]}"


def shorten(o: t.Any, max: int = 32, more: str = "...") -> str:
    s = str(o)
    return s[: max - len(more)] + more if len(s) > max else s


def shorten_many(
    objects: t.Sequence[t.Any],
    *,
    max_elems: int = 8,
    max_s: int = 16,
    more_elems: str = "...",
    more_s: str = "...",
) -> t.Generator[str, None, None]:
    if len(objects) >= max_elems:
        yield from map(str, objects)
        return

    for elem in objects[:max_elems]:
        yield shorten(elem, max_s, more_s)

    yield more_elems


def apply_f_to_interpolation_value(interpolation: Interpolation):
    value = convert(interpolation.value, interpolation.conversion)
    value = format(value, interpolation.format_spec)
    return value


# From https://peps.python.org/pep-0750/#example-implementing-f-strings-with-t-strings
def t_to_f_string(template: Template) -> str:
    parts = []
    for item in template:
        match item:
            case str() as s:
                parts.append(s)
            case Interpolation() as interp:
                parts.append(apply_f_to_interpolation_value(interp))
            case _:
                t.assert_never(item)

    return "".join(parts)


def join_t(delim: str | Template, iterable: t.Iterable[Template]) -> Template:
    iterator = iter(iterable)
    res = next(iterator, None)

    if res is None:
        return t""

    delim = delim if isinstance(delim, Template) else Template(delim)

    for elem in iterator:
        res += delim
        res += elem

    return res
