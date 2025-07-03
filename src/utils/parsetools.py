import datetime
from decimal import Decimal
import json
import re
from types import NoneType, UnionType
from typing import Any, Final, Union
import typing

PARSING_MAX_LENGTH: Final[int] = 2**20
ENCODING: Final[str] = 'utf-8'

EMPTY_JSON_STR: Final[str] = json.dumps("")
EMPTY_JSON_LIST: Final[str] = json.dumps([])
EMPTY_JSON_OBJ: Final[str] = json.dumps({})


# From https://stackoverflow.com/a/30928645/20895654
def json_depth(o: Any) -> int:
    if isinstance(o, dict) and o:
        return 1 + max(json_depth(o[a]) for a in o)
    if isinstance(o, list) and o:
        return 1 + max(json_depth(a) for a in o)
    return 0

type SupportedJsonTypesT = None | bool | int | float | str | list[SupportedJsonTypesT] | dict[str, SupportedJsonTypesT] | Any
type SupportedJsonTypesTypeT = type[None | bool | int | float | str] | list[SupportedJsonTypesTypeT] | dict[type[str], SupportedJsonTypesTypeT] | type[object] | UnionType


_NON_UNION_EXPECTED_TYPE = frozenset((NoneType, bool, int, float, str, object))

class StrictTypeError(ValueError):
    """The given strict_type is invalid"""

class WrongAmountOfArgs(ValueError):
    def __init__(self, given: tuple[int, ...], expected: int, *args: object) -> NoneType:
        super().__init__(*args)
        self.given = given
        self.expected = expected

class SafeJsonParser:
    MAX_LENGTH: int = PARSING_MAX_LENGTH

    def __init__(self, *, max_depth: int = -1, max_length: int = MAX_LENGTH, strict_type: SupportedJsonTypesTypeT = object) -> None:
        self.max_depth = max_depth
        self.max_length = max_length
        self.strict_type = strict_type

    def loads(self, s: str, **kwargs: Any) -> Any:  # type: ignore
        s = s.strip()
        length = len(s)

        if length > self.max_length:
            raise ValueError(length)
        
        try:
            result: Any = json.loads(s, **kwargs)
        except json.JSONDecodeError as e:
            raise e
        except RecursionError as e:
            raise e
        except Exception as e:
            raise e
        
        self.validate_json_type(result, self.strict_type)
        
        if self.max_depth >= 0 and (depth := json_depth(result)) > self.max_depth:
            raise RecursionError(depth)

        return result
    
    @classmethod
    def validate_json_type(cls, obj: SupportedJsonTypesT, strict_type: SupportedJsonTypesTypeT = object) -> None:
        if strict_type == object:
            return
        
        type_origin = typing.get_origin(strict_type)

        if type_origin in (Union, UnionType):
            success: bool = False
            for union_member in typing.get_args(strict_type):
                try:
                    cls.validate_json_type(obj, union_member)
                except TypeError:  # Fail, continue to next member and try it
                    continue
                else:    # Success, at least one member of the union didn't fail
                    success = True
                    # Success so rest of types get validated (example: we succeed but at the end we include bytes. If this is a valid strict_type, we wouldn't check then)
                    continue
            
            if success:
                return
            
            # Not a single union_member matched the type
            raise TypeError(obj, strict_type)

        if type_origin is None:
            type_origin = strict_type

        # Not isinstance because sees bool as int and more...
        if not type(obj) == type_origin:
            raise TypeError(obj, strict_type) 
        
        if isinstance(type_origin, list):
            # No elements
            if not type_origin or type_origin[0] == object:
                return

            expected_elems_type = type_origin[0]

            for child_obj in type_origin:
                cls.validate_json_type(child_obj, expected_elems_type)
        elif isinstance(type_origin)
        
        
        if not type_origin in _NON_UNION_EXPECTED_TYPE:
            raise StrictTypeError(type_origin)
        

        type_args = typing.get_args(strict_type)

        if not type_args:
            return
        
        
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


if __name__ == '__main__':
    print(Union[str], Union[(str,)], Union[(str, int)])
    
    # Single point of truth is type so we can use type checking; data -> type doesn't work
    type LiteralToStrPossibleT = bool | int | str
    LITERAL_TO_STR_POSSIBLE = frozenset(typing.get_args(LiteralToStrPossibleT.__value__))

    # Any of TYPES_LITERAL_ALLOWED or a list of any of TYPES_LITERAL_ALLOWED
    type AttributeValueParseTypesT = LiteralToStrPossibleT | list[LiteralToStrPossibleT]
    ATTRIBUTE_VALUE_PARSE_TYPES = LiteralToStrPossibleT.__value__ | list[LiteralToStrPossibleT.__value__]

    parser = SafeJsonParser(strict_type=ATTRIBUTE_VALUE_PARSE_TYPES)
    parser.loads('0.0')