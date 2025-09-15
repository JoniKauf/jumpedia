import datetime
from decimal import Decimal
import itertools
import json
import json.tool
import re
import shlex
from types import NoneType, UnionType
from typing import Any, Final, Mapping, Never, Self, Sequence, TypeIs, Union
import typing
import json
from typing_extensions import Sentinel, TypeForm
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

# Because list and dict are not covariant, we have to use other ways. This is a known issue.
type SupportedJsonTypesT = None | bool | int | float | str | Sequence[SupportedJsonTypesT] | Mapping[str, SupportedJsonTypesT]

# This represents the strict type. 
# A literal tuple represents a union. 
# There are two variants, the ...NoUnionT is there to not allow nested tuples/unions. 
type SupportedJsonTypesTypeNoUnionT = type[None | bool | int | float | str] | list[SupportedJsonTypesTypeT] | dict[type[str], SupportedJsonTypesTypeT] | type[Anything]
type SupportedJsonTypesTypeT = SupportedJsonTypesTypeNoUnionT | tuple[SupportedJsonTypesTypeNoUnionT, ...]

_NON_UNION_EXPECTED_TYPE = frozenset((NoneType, bool, int, float, str))

class Anything:
    def __new__(cls) -> Never:
        raise RuntimeError()



class StrictTypeError(ValueError):
    """The given strict_type is invalid"""

class TooManyArgs(ValueError):
    def __init__(self, given: int, max: int, *args: object) -> NoneType:
        super().__init__(*args)
        self.given = given
        self.max = max

class SafeJsonParser[T: SupportedJsonTypesT]:
    MAX_LENGTH: int = PARSING_MAX_LENGTH

    def __init__(self, *, max_depth: int = -1, max_length: int = MAX_LENGTH, strict_type: SupportedJsonTypesTypeT = Anything) -> None:
        self.max_depth = max_depth
        self.max_length = max_length
        self.strict_type = strict_type

    def loads(self, s: str, **kwargs: Any) -> T:  # type: ignore
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
    def validate_json_type(cls, obj: SupportedJsonTypesT, strict_type: SupportedJsonTypesTypeT = Anything) -> None:
        if strict_type == Anything:
            return
        
        type_origin = typing.get_origin(strict_type)

        if type_origin is None:
            type_origin = strict_type
        
        # Ex: [str]
        if isinstance(type_origin, list):
            if not isinstance(obj, list):
                raise TypeError

            if len(type_origin) > 1:
                raise TooManyArgs(len(type_origin), 1)
            
            if not type_origin:
                return
            
            expected_elems_type = type_origin[0]

            if expected_elems_type == Anything:
                return

            for child_obj in obj:
                cls.validate_json_type(child_obj, expected_elems_type)

            return

        # Ex: {str: int}
        if isinstance(type_origin, dict):
            if not isinstance(obj, dict):
                raise TypeError
            
            if len(type_origin) > 1:
                raise TooManyArgs(len(type_origin), 1)
            
            if not type_origin:
                return
            
            expected_k_type, expected_v_type = next(iter(type_origin.items()))

            if expected_v_type != str:
                raise StrictTypeError("Key must be type of str")
            
            for child_k, child_v in obj.items():
                if not isinstance(child_k, expected_k_type):
                    raise TypeError("Dict key not str")
                
                if expected_v_type != Anything:
                    cls.validate_json_type(child_v, expected_v_type)

            return

        if isinstance(type_origin, tuple):
            success: bool = False
            
            for union_member in type_origin:
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
        
        if not type_origin in _NON_UNION_EXPECTED_TYPE:
            raise StrictTypeError(type_origin)
   
        if typing.get_args(strict_type):
            raise StrictTypeError
        
        # Not isinstance because sees bool as int and more...
        if not type(obj) == type_origin:
            raise TypeError(obj, strict_type)  
            
        
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



class ArgParser:
    # From https://www.fileformat.info/info/unicode/block/general_punctuation/utf8test.htm
    CLEAN_MAP: dict[str, str] = {
        '\'': "‘’‚‛",
        '"': "”“„‟"
    }

    def __init__(self) -> None:
        pass 

    def _clean(self, s: str, /) -> str:
        s = s.strip()

        for k, v in self.__class__.CLEAN_MAP:
            s = re.sub(rf'[{re.escape(v)}]', k, s)
        
        return s
    
    def parse_args(self, s: str, /) -> list[str]:
        s = self._clean(s)

        result: list[str] = []
        in_quotes: bool = False
        in_escape: bool = False
        current_arg: list[str] = []
        prev_c: str = ''
        COUNT = len(s)

        for i, c in enumerate(s):
            if in_escape:
                if c not in '\\"':
                    raise ValueError('\\ not followed by " or \\')
                
                current_arg.append(c)
                in_escape = False
            
            elif not in_escape and c == '\\':
                in_escape = True
                
            elif c == '"':
                if in_quotes:
                    result.append(''.join(current_arg))
                    current_arg = []

                    if i < COUNT - 1 and not s[i + 1].isspace():
                        raise ValueError('Closing " not proceded by whitespace')
                else:
                    if not prev_c.isspace():
                        raise ValueError('Opening " not preceded by whitespace')
                
                in_quotes = not in_quotes

            else:
                if in_quotes:
                    current_arg.append(c)
                else:
                    if c.isspace():
                        if not prev_c.isspace():
                            result.append(''.join(current_arg))
                            current_arg = []
                    else:
                        current_arg.append(c)
                    
            prev_c = c
        
        if in_escape:
            raise ValueError('Not escaped final \\')
        
        if in_quotes:
            raise ValueError('Not closed quotation mark')
        
        if current_arg:
            result.append(''.join(current_arg))

        return result