import decimal
import json
import re
import string
from typing import Any, Container, Iterable
from discordtools import feedbackerrors as fbe
import datetime as dt

PASCAL_REPLACE_PATTERN = re.compile(r'(?!^)([A-Z]+)')

def pascal_to_snake(s: str):
    return re.sub(PASCAL_REPLACE_PATTERN, r'_\1', s).lower()


ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+')

def fix_whitespace(s: str, repl: str, strip: bool) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)


IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + '_')

def invalid_identifier_chars(s: str) -> set[str]:
    return set(char for char in s if char not in IDENTIFIER_CHARS)

def norm(s: str, whitespace_repl: str = '_') -> str:
    return fix_whitespace(s.casefold(), whitespace_repl, True) 

def fix_aliases(aliases: Iterable[str], max_length: int, max_aliases: int) -> set[str]:
    result: set[str] = set()

    for alias in frozenset(aliases):
        alias = norm(alias)

        if len(alias) > max_length:
            raise 

    if (length := len(result)) > max_aliases:
        raise fbe.TemporaryFeedbackError(length, max_aliases)
    
    return result


def create_name_and_display_name(bad_name: str, identifiers_only: bool, max_length: int, existing_names: Iterable[str]) -> tuple[str, str]:
    name: str = norm(bad_name)
    
    if (length := len(name)) > max_length:
        raise fbe.TemporaryFeedbackError(length, max_length)
    
    if identifiers_only and (inv := invalid_identifier_chars(name)):
        raise fbe.TemporaryFeedbackError(inv)
    
    if name in existing_names:
        raise fbe.TemporaryFeedbackError()
    
    display_name: str = fix_whitespace(bad_name, ' ', False)

    return (name, display_name)