import datetime
from decimal import Decimal
import json
import re
from types import NoneType
from typing import Any, Final
import typing
from errors.feedback import feedbacks

DEFAULT_MAX_LENGTH: Final[int] = 2**20
ENCODING: Final[str] = 'utf-8'

EMPTY_JSON_STR: Final[str] = '""'
EMPTY_JSON_LIST: Final[str] = '[]'
EMPTY_JSON_OBJ: Final[str] = '{}'


# From https://stackoverflow.com/a/30928645/20895654
def json_depth(o: Any) -> int:
    if isinstance(o, dict) and o:
        return 1 + max(json_depth(o[a]) for a in o)
    if isinstance(o, list) and o:
        return 1 + max(json_depth(a) for a in o)
    return 0

type SupportedTypesT = None | bool | int | float | str | list[SupportedTypesT] | dict[str, SupportedTypesT] | Any

def validate_json_loaded_is_strict_type_simple(obj: SupportedTypesT, expected_type: type[SupportedTypesT] | None | NoneType = Any) -> None:  # type: ignore
    if expected_type == Any:
        return
    
    type_origin = typing.get_origin(expected_type)

    if expected_type in (None, type[None], NoneType):
        type_origin = NoneType
    elif type_origin is None:
        type_origin = expected_type

    if not isinstance(obj, type_origin):
        raise TypeError(obj, expected_type)
    
    type_args = typing.get_args(expected_type)

    if not type_args:
        return
    
    if isinstance(obj, list):
        type_elems = type_args[0]

        if type_elems == Any:
            return
        
        for child_obj in obj:
            validate_json_loaded_is_strict_type_simple(child_obj, type_elems)

    elif isinstance(obj, dict):
        type_k = type_args[0]
        type_v = Any

        if len(type_args) > 1:
            type_v = type_args[1]
        
        for k, v in obj.items():
            validate_json_loaded_is_strict_type_simple(k, type_k)
            validate_json_loaded_is_strict_type_simple(v, type_v)  # type: ignore
    


def json_loads_safe(s: str, max_depth: int = -1, max_length: int = DEFAULT_MAX_LENGTH, strict_type: type[SupportedTypesT] | None = Any, **kwargs: Any) -> Any:  # type: ignore
    s = s.strip()
    length = len(s)

    if length > max_length:
        raise feedbacks.temp(length, max_length)
    
    try:
        result: Any = json.loads(s, **kwargs)
    except json.JSONDecodeError as e:
        raise e
    except RecursionError as e:
        raise RecursionError(None, max_depth, e)
    except Exception as e:
        raise e
    
    validate_json_loaded_is_strict_type_simple(result, strict_type)
    
    if max_depth >= 0 and (depth := json_depth(result)) > max_depth:
        raise RecursionError(depth, max_depth)

    return result


# Regex and function created by Joni. If you use it, mention me if u wanna be cool af :)
_TIMEDELTA_PARSE_PATTERN = re.compile(r'''
    ([-+])?               # [Group 1: Optional '-' or '+' sign]
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        ([0-9]+)              # [Group 2: Any digit 0 to ∞ times]
        \s*                   # Whitespace 0 to ∞ times
        (d|days?)             # [Group 3: 'd', 'day' or 'days']
    )?                    # End group, its insides must either fully match or not exist at all
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        ([0-1]?[0-9]|2[0-3])  # [Group 4: 0 to 23] with optional leading 0 for single digit numbers
        \s*                   # Whitespace 0 to ∞ times
        (h|hrs?|hours?)       # [Group 5: 'h', 'hr', 'hrs', 'hour' or 'hours']
    )?                    # End group, its insides must either fully match or not exist at all
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        ([0-5]?[0-9])         # [Group 6: 0 to 59] with optional leading 0 for single digit numbers
        \s*                   # Whitespace 0 to ∞ times
        (m|mins?|minutes?)    # [Group 7: 'm', 'min', 'mins', 'minute' or 'minutes']
    )?                    # End group, its insides must either fully match or not exist at all
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        (                     # [Group 8: 
            [0-5]?[0-9]           # 0 to 59, with optional leading 0 for single digit numbers
            (?:[.,][0-9]*)?       # followed by optional: '.' or ',' followed by any digits 0 to ∞ times
        )                     # ]
        \s*                   # Whitespace 0 to ∞ times
        (s|secs?|seconds?)    # [Group 9: 's', 'sec', 'secs', 'second' or 'seconds']
    )?                    # End group, its insides must either fully match or not exist at all
''', re.VERBOSE | re.IGNORECASE)


def parse_timedelta(s: str) -> datetime.timedelta:
    match = _TIMEDELTA_PARSE_PATTERN.match(s.strip())

    if match is None:
        raise ValueError("Invalid timedelta format")

    # Pairs of unit and value, possibly with single sign at the end
    groups = [g for g in reversed(match.groups()) if g is not None]

    if len(groups) < 2:
        raise ValueError("Timedelta format is either empty or only a sign")
    
    total_seconds = Decimal()
    sign = 1

    if groups[-1] in '-+':
        if groups[-1] == '-':
            sign = -1

        groups.pop()

    for i in range(0, len(groups), 2):
        unit = groups[i][0].lower()
        value = Decimal(groups[i + 1].replace('.', ',', 1))

        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60
        else:
            total_seconds += value
    
    try:
        return datetime.timedelta(seconds=float(total_seconds * sign))
    except Exception:
        raise ValueError("Number too small or big")
    

def unparse_timedelta(obj: datetime.timedelta) -> str:
    if obj.total_seconds() < 0:
        parts: list[str] = ["-"]
    else:
        parts: list[str] = []
    
    mins, seconds = divmod(obj.seconds, 60)
    hours, mins = divmod(mins, 60)

    if obj.microseconds:
        seconds += (obj.microseconds / 1_000_000)

    if obj.days: 
        parts.append(f"{abs(obj.days)}d")
    if hours: 
        parts.append(f"{abs(hours)}h")
    if mins: 
        parts.append(f"{abs(mins)}m")
    if seconds:
        parts.append(f"{abs(seconds)}s")
        
    return ''.join(parts)