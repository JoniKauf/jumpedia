from enum import Enum
import re
import string
from string.templatelib import Interpolation, Template
from typing import Any, NewType, assert_never, Callable, Container, Final, Generator, Iterable, Literal, Sequence
from collections.abc import Set

from errors.feedback import feedbacks

ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+', re.UNICODE)
IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + '_')

BAD_CHAR_MAPPING = str.maketrans({
    '‘': "'",
    '’': "'",
    '‚': "'",
    '‛': "'",
    '“': '"',
    '”': '"',
    '„': '"',
    '‟': '"'
})

def pascal_to_snake(s: str):
    return s[0].lower() + ''.join(f'_{c.lower()}' if c.isupper() else c for c in s[1:])

def replace_whitespace_groups(s: str, repl: str, strip: bool = True) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)

def replace_bad_chars(s: str) -> str:
    return s.translate(BAD_CHAR_MAPPING)

def invalid_identifier_chars(s: str) -> set[str]:
    return set(char for char in s if char not in IDENTIFIER_CHARS) 

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



# We don't use NewType just yet, because it has some drawbacks
# Mostly for us it matters that it still isn't valid in TypeForm[...]
# as of writing this.
class RealStr(str): pass
class NormStr(RealStr): pass

def raw_to_real(raw: str, /) -> RealStr:
    raw = replace_whitespace_groups(raw, ' ', True)
    raw = replace_bad_chars(raw)
    raw = ''.join(c for c in raw if c.isprintable())

    if not raw:
        raise ValueError('empty result')
    
    return RealStr(raw)

def real_to_norm(real: RealStr, /) -> NormStr:
    return NormStr(real.lower())

def raw_to_norm(raw: str, /) -> NormStr:
    return real_to_norm(raw_to_real(raw))

def raw_to_real_and_norm(raw: str, /) -> tuple[RealStr, NormStr]:
    real = raw_to_real(raw)
    return real, real_to_norm(real)

def raws_to_unique_reals_and_norms(raws: Iterable[str], /, strict: bool = False) -> tuple[tuple[RealStr, ...], tuple[NormStr, ...]]:
    norm_to_real: dict[NormStr, RealStr] = {}

    for raw in raws:
        real, norm = raw_to_real_and_norm(raw)

        if norm in norm_to_real:
            if strict and norm_to_real[norm] != real:
                raise ValueError("normed equal strings are not equal when real")
        else:
            norm_to_real[norm] = real

    # Dict guarantees order for python 3.8+
    return (tuple(norm_to_real.values()), tuple(norm_to_real.keys()))


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