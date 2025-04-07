import re
import string
from discordtools import feedbackerrors as fbe

PASCAL_REPLACE_PATTERN = re.compile(r'(?!^)([A-Z]+)')

def pascal_to_snake(s: str):
    return re.sub(PASCAL_REPLACE_PATTERN, r'_\1', s).lower()


ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+')

def fix_whitespace(s: str, repl: str) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s)


IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + '_')

def invalid_identifier_chars(s: str) -> set[str]:
    return set(char for char in s if char not in IDENTIFIER_CHARS)