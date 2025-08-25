from enum import Enum
import re
import string
from string.templatelib import Interpolation, Template
from typing import Any, assert_never, Callable, Container, Final, Generator, Iterable, Literal, Sequence
from collections.abc import Set

from errors.feedback import feedbacks

PASCAL_REPLACE_PATTERN = re.compile(r'(?!^)([A-Z]+)')
ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+')
IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + '_')

def pascal_to_snake(s: str):
    return re.sub(PASCAL_REPLACE_PATTERN, r'_\1', s).lower()

def fix_whitespace(s: str, repl: str, strip: bool = True) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)

def invalid_identifier_chars(s: str) -> set[str]:
    return set(char for char in s if char not in IDENTIFIER_CHARS) 

def valnitize_many(s: Sequence[str], min_count: int, max_count: int, min_length: int, max_length: int) -> Generator[str, None, None]:
    if isinstance(s, str):
        raise ValueError
    
    count = len(s)

    if not (min_count <= count <= max_count):
        raise ValueError(s, count)
    
    for elem in s:
        yield raw_to_real_and_validate(elem, min_length, max_length)

def human_join(objects: Sequence[Any], final_delimiter: str, delimiter: str = ", ") -> str:
    objects_str = tuple(map(str, objects))

    if len(objects) <= 1:
        return delimiter.join(objects_str)
    
    return f"{delimiter.join(objects_str[:-1])}{final_delimiter}{objects[-1]}"

def shorten(o: Any, max: int = 32, more: str = '...') -> str:
    s = str(o)
    return s[:max - len(more)] + more if len(s) > max else s

def shorten_many(objects: Sequence[Any], *, max_elems: int = 8, max_s: int = 16, more_elems: str = '...', more_s: str = '...') -> Generator[str, None, None]:
    if len(objects) >= max_elems:
        yield from map(str, objects)
        return
    
    for elem in objects[:max_elems]:
        yield shorten(elem, max_s, more_s)

    yield more_elems


def raw_to_real(raw: str, /) -> str:
    raw = fix_whitespace(raw, ' ', True) 
    return ''.join(c for c in raw if c.isprintable())

def raw_to_norm(raw: str, /, *, already_sanitized: bool = False) -> str:
    if not already_sanitized:
        raw = raw_to_real(raw)

    raw = raw.lower()

    return raw

def raw_to_real_and_norm(raw: str, /) -> tuple[str, str]:
    raw = raw_to_real(raw)

    return raw, raw_to_norm(raw, already_sanitized=True)

def raws_to_unique_reals_and_norms(raws: Iterable[str], /, *, strict: bool = False) -> tuple[tuple[str, str], ...]:
    norm_to_real: dict[str, str] = {}

    for raw in raws:
        real, norm = raw_to_real_and_norm(raw)

        if norm in norm_to_real:
            if strict and norm_to_real[norm] != real:
                raise ValueError("normed equal strings are not equal when real")
        else:
            norm_to_real[norm] = real

    return tuple(norm_to_real.items())

def raw_to_real_and_validate(s: str, min_length: int, max_length: int) -> str:
    name = raw_to_real(s)
    length = len(name)

    if not (min_length <= length <= max_length):
        raise ValueError(s, length)
    
    return name



def _convert(value: object, conversion: Literal["a", "r", "s"] | None) -> object:
    if conversion == "a":
        return ascii(value)
    elif conversion == "r":
        return repr(value)
    elif conversion == "s":
        return str(value)
    return value

# From https://peps.python.org/pep-0750/#example-implementing-f-strings-with-t-strings
def t_to_f_string(template: Template) -> str:
    parts = []
    for item in template:
        match item:
            case str() as s:
                parts.append(s)
            case Interpolation(value, _, conversion, format_spec):
                value = _convert(value, conversion)
                value = format(value, format_spec)
                parts.append(value)
            case _:
                assert_never(item)
                
    return "".join(parts)