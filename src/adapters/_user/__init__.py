
import re

MENTION_PATTERN = re.compile(r'^<@([0-9]{0,20})>$')

def _int_to_id(i: int) -> int:
    MAX = (2 ** 64 - 1)

    if 0 > i > MAX:
        raise ValueError('Out of range')
    
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
    