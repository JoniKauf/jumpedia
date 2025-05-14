import decimal
import json
import re
import string
from typing import Any, Callable, Container, Final, Iterable, Sequence
from discordtools import feedbackerrors as fbe
import datetime as dt
from collections.abc import Set

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
    result: set[str] = set()

    for alias in frozenset(aliases):
        alias = norm(alias)

        if len(alias) > max_length:
            raise 

    if (length := len(result)) > max_aliases:
        raise fbe.TemporaryFeedbackError(length, max_aliases)
    
    return result

def sanitize(s: str, whitespace_repl: str = ' ') -> str:
    s = fix_whitespace(s, whitespace_repl, True) 
    return ''.join(c for c in s if c.isprintable())

def norm(s: str, whitespace_repl: str = '_') -> str:
    return NORMALIZE_FUNC(sanitize(s, whitespace_repl))

def norm_syn(s: str) -> str:
    return norm(s, ' ')

def validate_and_sanitize_name(bad_name: str, max_length: int, forbidden: Iterable[str]) -> str:
    name = sanitize(bad_name)
    
    if not name:
        raise fbe.TemporaryFeedbackError("Name is empty or just spaces.")
    
    if (length := len(name)) > max_length:
        raise fbe.TemporaryFeedbackError("Too long name", name, length, max_length)
    
    if NORMALIZE_FUNC(name) in (NORMALIZE_FUNC(f) for f in forbidden):
        raise fbe.TemporaryFeedbackError("Name is already taken.")
    
    return name

def validate_and_norm_aliases(bad_aliases: Iterable[str], max_length: int, max_count: int, forbidden: Iterable[str]) -> set[str]:
    result: set[str] = set()

    forbidden = frozenset(NORMALIZE_FUNC(f) for f in forbidden)

    for alias in bad_aliases:
        alias = norm_syn(alias)

        if not alias:
            continue

        if (length := len(alias)) > max_length:
            raise fbe.TemporaryFeedbackError("Too long alias", alias, length, max_length)
        
        if alias in forbidden:
            raise fbe.TemporaryFeedbackError("Not allowed alias (already taken)", alias, forbidden)
        
        result.add(alias)
        
    if (count := len(result)) > max_count:
        raise fbe.TemporaryFeedbackError("Too many aliases", result, count, max_count)
    
    return result

def validate_and_sanitize_or_norm_syns(bad_name: str, bad_aliases: Iterable[str], max_length: int, max_count: int, forbidden: Iterable[str]) -> tuple[str, set[str]]:
    forbidden = tuple(forbidden)

    name = validate_and_sanitize_name(bad_name, max_length, forbidden)
    aliases = validate_and_norm_aliases(bad_aliases, max_length, max_count, forbidden)

    if name in aliases:
        aliases.remove(name)
    elif (count := len(aliases)) > max_count:
        # Retest count because above we didn't subtract one to account for name
        # possibly being in, but because now we know it isn't in, it could be 1 too many
        raise fbe.TemporaryFeedbackError("Too many aliases", aliases, count, max_count)

    return (name, aliases)