from numbers import Real
import re
import string
import typing as t
from dataclasses import dataclass, field
from string.templatelib import Interpolation, Template, convert

ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r"\s+", re.UNICODE)
IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + "_")

BAD_CHAR_MAPPING = str.maketrans(
    {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"', "‟": '"'}
)


def pascal_to_snake(s: str, /, delim: str = "_"):
    return s[0].lower() + "".join(
        f"{delim}{c.lower()}" if c.isupper() else c for c in s[1:]
    )


def replace_whitespace_groups(s: str, repl: str, strip: bool = True) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)


def replace_bad_chars(s: str) -> str:
    return s.translate(BAD_CHAR_MAPPING)


def invalid_identifier_chars(s: str) -> set[str]:
    return set(char for char in s if char not in IDENTIFIER_CHARS)


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


class RealStr(str):
    def __new__(cls, s: str) -> t.Self:
        if isinstance(s, cls):
            return s

        s = replace_whitespace_groups(s, " ", True)
        s = replace_bad_chars(s)
        s = "".join(c for c in s if c.isprintable())

        if not s:
            raise ValueError("empty result")

        return super().__new__(cls, s)


class NormStr(str):
    def __new__(cls, s: str) -> t.Self:
        if not isinstance(s, RealStr):
            s = RealStr(s)

        return super().__new__(cls, s.lower())


    @classmethod
    def unique_reals_and_norms(
        cls, iterable: t.Iterable[str], /
    ) -> tuple[tuple[RealStr, ...], tuple[t.Self, ...]]:
        mapping: dict[t.Self, RealStr] = {}

        for s in iterable:
            real_s = RealStr(s)
            norm = cls(real_s)

            del s

            existing_norm = mapping.get(norm)

            if existing_norm is not None:
                raise ValueError(real_s, existing_norm)

            mapping[norm] = real_s

        # Dict order is preserved
        return (tuple(mapping.values()), tuple(mapping))


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
                assert_never(item)

    return "".join(parts)
