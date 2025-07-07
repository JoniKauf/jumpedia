from enum import Enum
import re
import string
from typing import Any, Callable, Container, Final, Generator, Iterable, Literal, Sequence
from collections.abc import Set

from errors.feedback import feedbacks

PASCAL_REPLACE_PATTERN = re.compile(r'(?!^)([A-Z]+)')
ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+')
IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + '_')
NORMALIZE_FUNC: Final[Callable[[str], str]] = str.lower  # We use lower because str stays same size

def pascal_to_snake(s: str):
    return re.sub(PASCAL_REPLACE_PATTERN, r'_\1', s).lower()

def fix_whitespace(s: str, repl: str, strip: bool = True) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)

def invalid_identifier_chars(s: str) -> set[str]:
    return set(char for char in s if char not in IDENTIFIER_CHARS)

def fix_aliases(aliases: Iterable[str], max_length: int, max_aliases: int) -> set[str]:
    from discordtools import feedbackerrors as fbe

    result: set[str] = set()

    for alias in frozenset(aliases):
        alias = norm(alias)

        if len(alias) > max_length:
            raise 

    if (length := len(result)) > max_aliases:
        raise fbe.TemporaryFeedbackError(length, max_aliases)
    
    return result

def norm(s: str, whitespace_repl: str = '_') -> str:
    return NORMALIZE_FUNC(sanitize(s, whitespace_repl))

def norm_syn(s: str) -> str:
    return norm(s, ' ')

def sanitize(s: str, whitespace_repl: str = ' ') -> str:
    s = fix_whitespace(s, whitespace_repl, True) 
    return ''.join(c for c in s if c.isprintable())

def valnitize(s: str, min_length: int, max_length: int) -> str:
    name = sanitize(s)
    length = len(name)

    if not (min_length <= length <= max_length):
        raise feedbacks.temp(f"Name must be between", min_length, "and", max_length, "characters long")
    
    return name

# def validate_and_sanitize_aliases(bad_aliases: Iterable[str], max_length: int, max_count: int, forbidden: Iterable[str] = ()) -> set[str]:
#     from discordtools import feedbackerrors as fbe

#     result: set[str] = set()

#     forbidden = frozenset(NORMALIZE_FUNC(f) for f in forbidden)

#     for alias in bad_aliases:
#         alias = sanitize(alias)

#         if not alias:
#             continue

#         if (length := len(alias)) > max_length:
#             raise fbe.TemporaryFeedbackError("Too long alias", alias, length, max_length)
        
#         if alias in forbidden:
#             raise fbe.TemporaryFeedbackError("Not allowed alias (already taken)", alias, forbidden)
        
#         result.add(alias)
        
#     if (count := len(result)) > max_count:
#         raise fbe.TemporaryFeedbackError("Too many aliases", result, count, max_count)
    
#     return result

# def validate_and_sanitize_syns(bad_name: str, bad_aliases: Iterable[str], max_length: int, max_count: int, forbidden: Iterable[str] = ()) -> tuple[str, set[str]]:
#     from discordtools import feedbackerrors as fbe
    
#     forbidden = tuple(forbidden)

#     name = valnitize(bad_name, max_length, forbidden)
#     aliases = validate_and_sanitize_aliases(bad_aliases, max_length, max_count, forbidden)

#     if name in aliases:
#         aliases.remove(name)
#     elif (count := len(aliases)) > max_count:
#         # Retest count because above we didn't subtract one to account for name
#         # possibly being in, but because now we know it isn't in, it could be 1 too many
#         raise fbe.TemporaryFeedbackError("Too many aliases", aliases, count, max_count)

#     return (name, aliases)

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

