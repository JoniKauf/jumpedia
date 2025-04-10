import re
import string
from typing import Container, Iterable
from discordtools import feedbackerrors as fbe

PASCAL_REPLACE_PATTERN = re.compile(r'(?!^)([A-Z]+)')

def pascal_to_snake(s: str):
    return re.sub(PASCAL_REPLACE_PATTERN, r'_\1', s).lower()


ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+')

def fix_whitespace(s: str, repl: str, strip: bool = True) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)


IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + '_')

def invalid_identifier_chars(s: str) -> set[str]:
    return set(char for char in s if char not in IDENTIFIER_CHARS)


def create_name_and_display_name(bad_name: str, identifiers_only: bool, existing_names: Iterable[str] = ()) -> tuple[str, str]:
    tidy_name: str = bad_name.strip()

    name: str = fix_whitespace(tidy_name, '_').lower()

    if identifiers_only and (inv := invalid_identifier_chars(name)):
        raise ValueError(inv)
    
    if name in existing_names:
        raise ValueError()
    
    display_name: str = fix_whitespace(tidy_name, " ")

    return (name, display_name)
        
    


    