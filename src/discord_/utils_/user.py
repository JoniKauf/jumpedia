import re
import typing as t

MAX_NAME_LENGTH: t.Final[int] = 32

MIN_ID: t.Final[int] = 0
MAX_ID: t.Final[int] = 2**64 - 1  # Snowflake is Unsigned Long int

MENTION_PATTERN = re.compile(r"^<@([0-9]{0,20})>$")


def _int_to_id(i: int) -> int:
    if not (MIN_ID <= i <= MAX_ID):
        raise ValueError("Out of range")

    return i


def _str_to_id(s: str) -> int:
    try:
        identifier = int(s)
    except ValueError:
        pass
    else:
        return _int_to_id(identifier)

    s = s.strip()

    match = MENTION_PATTERN.match(s)

    if not match:
        raise ValueError

    return int(match.group(1))


def identifier_to_id(identifier: str | int) -> int:
    if isinstance(identifier, int):
        return _int_to_id(identifier)

    return _str_to_id(identifier)
