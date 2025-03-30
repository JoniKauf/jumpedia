import enum
from trickjump.context import Context
import datetime as dt
import functools
import json
from threading import Lock
from typing import Any, Iterable, Literal, Optional as Opt, Sequence
from discordtools import feedbackerrors as fbe
import re
from collections2 import tree
from trickjump.community import Community
import builtins
from collections2.range import Range
from decimal import Decimal
import decimal


#------#   Module Constants & Helper Functions   #------#

type AttrT = 'Attribute'

type AttributeValueTypeT = (
    bool | int | Decimal | 
    dt.time | dt.date | dt.datetime | dt.timedelta | 
    str
)

class AttributeValueTypeEnum(enum.Enum):
    boolean = bool
    integer = int
    decimal = Decimal
    time = dt.time
    date = dt.date
    date_and_time = dt.datetime
    time_span = dt.timedelta
    text = str

AttributeValueTypes: set[type[AttributeValueTypeT]] = {elem.value for elem in AttributeValueTypeEnum}

_ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+')
_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')
_VALID_SYN_CHARS: set[str] = set('abcdefghijklmnopqrstuvwxyz_0123456789')

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

def _parse_timedelta(s: str) -> dt.timedelta:
    match = _TIMEDELTA_PARSE_PATTERN.match(s.strip())

    if match is None:
        raise fbe.TemporaryFeedbackError("Invalid timedelta format")

    # Pairs of unit and value, possibly with single sign at the end
    groups = [g for g in reversed(match.groups()) if g is not None]

    if len(groups) < 2:
        raise fbe.TemporaryFeedbackError("Timedelta format is either empty or only a sign")
    
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
        return dt.timedelta(seconds=float(total_seconds * sign))
    except Exception:
        raise fbe.TemporaryFeedbackError("Number too small or big")
    

#------#   Attribute   #------#	

class Attribute[T: AttributeValueTypeT]:
    """Represent an attribute of a Trickjump.

    In a relational database model 'Trickjump' would represent a table,
    'Attribute' a column and specific values interacting with the
    'Attribute' class would be rows.

    Instead of specific types, values are passed in mostly as str, None
    or other basic data types, which are especially supported by discord.py.
    """

    # --- CONSTANTS ---

    # General
    MAX_SYN_LEN = 32
    MAX_ATTRIBUTES_PER_COMMUNITY = 50
    MAX_VALUE_SLOTS = 32

    # int | decimal
    NUMBER_MAX: int = 2 ** 63 - 1
    NUMBER_MIN: int = -NUMBER_MAX - 1
    DECIMAL_PRECISION: int = decimal.getcontext().prec
    INT_PART_MAX_LEN: int = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
    DEC_PART_MAX_LEN: int = DECIMAL_PRECISION - INT_PART_MAX_LEN
    DECIMAL_MAX_LEN: int = DECIMAL_PRECISION if DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1
    
    # str
    STR_MAX_LEN = 512

    # Collection
    COLLECTION_MAX_MEMORY = 1024 * 32
    COLLECTION_MAX_ELEMS = 1024

    MAX_DEPTH = 64

    # --- CLASS CONSTANTS ---

    CREATION_LOCK = Lock()
    LOOKUP: dict[Community, dict[str, 'Attribute']] = {}

    SORT_KEY_LAST_NUMBER = max(abs(NUMBER_MIN), abs(NUMBER_MAX)) + 1
    
    # --- Init ---

    def __init__(
        self, 
        community: Community,
        name: str,
        alias: Iterable[str],
        value_type: type[T],
        value_collection: None | Sequence[tuple[T, int]] | tree.TreeT[tuple[T, int]],
        min_value_slots: int,
        max_value_slots: int,
        unique_slots: bool,
        unique_values_per_list: bool,
        user_bound: bool
    ):
        with Attribute.CREATION_LOCK:
            # --- BASIC ASSIGNMENTS ---
            self._community = community

            if value_type not in set(vt.value for vt in AttributeValueTypeEnum):
                raise TypeError
            self._value_type = value_type

            if min_value_slots < 0:
                raise fbe.TemporaryFeedbackError
            if max_value_slots < 1 or max_value_slots < min_value_slots or max_value_slots > Attribute.MAX_VALUE_SLOTS:
                raise fbe.TemporaryFeedbackError
            self._min_value_slots = min_value_slots
            self._max_value_slots = max_value_slots

            self._unique_slots = unique_slots

            if unique_values_per_list and user_bound:
                raise fbe.TemporaryFeedbackError("A user bound attribute cannot be set to be unique per list.")
            
            self._unique_value_per_list = unique_values_per_list
            self._user_bound = user_bound

            # --- NAME & ALIAS ---
            self._name = self._normalize_and_validate_syn(name)
            self._alias = set(self._normalize_and_validate_syn(a) for a in alias)
            
            # --- COLLECTION SETUP ---
            self._list: Opt[None | list[T]] = None
            self._tree: Opt[tree.Tree] = None

            self._sort_value: dict[T, int] = {}
            self._unnormalize: dict[T, T] = {}

            if not value_collection:
                pass
            elif isinstance(value_collection, Sequence):
                self._list = []

                for value in value_collection:
                    v_norm = self._normalize_and_implement_value(value)
                    self._list.append(v_norm)
                    
                if len(self._list) > Attribute.COLLECTION_MAX_ELEMS:
                    raise fbe.TemporaryFeedbackError
                
                if sum(self.value_to_memory(v) for v in self._list) > Attribute.COLLECTION_MAX_MEMORY:
                    raise fbe.TemporaryFeedbackError
            else:
                try:
                    self._tree = tree.Tree(
                        value_collection, 
                        self._normalize_and_implement_value, 
                        Attribute.MAX_DEPTH, 
                        Attribute.COLLECTION_MAX_ELEMS, 
                        Attribute.NUMBER_MAX
                    )
                except tree.TreeError as e:
                    raise fbe.TemporaryFeedbackError(e)
                
                if sum(
                    self.value_to_memory(n.value) 
                    for n in self._tree._node_lookup.values()
                ) > Attribute.COLLECTION_MAX_MEMORY:
                    raise fbe.TemporaryFeedbackError
            
            # --- DANGER ZONE ---
            lookup = Attribute.LOOKUP.setdefault(community, {})

            for syn in (name, *alias):
                lookup[syn] = self
                
            # TODO:
            # - Add to database
            # - Make everything string based

    @classmethod
    def init_for_discord_command(
        cls,
        community: Community,
        name: str,
        alias: str,
        value_type: AttributeValueTypeEnum,
        value_collection: str,
        min_value_slots: int,
        max_value_slots: int,
        unique_slots: bool,
        unique_values_per_list: bool,
        user_bound: bool
    ) -> 'Attribute':
        # vc_tmp should be one of the following to be valid (tuple syntax for inner list):
        # list[T], list[list[T, int]], TreeT[T], TreeT[list[T, int]]
        if not value_collection:
            return Attribute(
                community,
                name,
                alias,
                value_type.value,  
                None,
                min_value_slots,
                max_value_slots,
                unique_slots,
                unique_values_per_list,
                user_bound
            )

        try:
            vc_tmp: Any = json.loads(value_collection)
        except json.JSONDecodeError:
            raise fbe.TemporaryFeedbackError
        
        if not isinstance(vc_tmp, (list, dict)):
            raise fbe.TemporaryFeedbackError("Must be list or tree")
        
        if not vc_tmp:
            raise fbe.TemporaryFeedbackError("Empty collection")

        simple: bool = not isinstance(next(iter(vc_tmp)), list)

        result = 
        for i, elem in enumerate(vc_tmp):
            if isinstance(elem, list):
                if simple:
                    raise fbe.TemporaryFeedbackError("All elems but be either a list or not")

                if len(elem) != 2:
                    raise fbe.TemporaryFeedbackError("Length 2 list required")
                
                sort_value = elem[1]

                if not isinstance(sort_value, int):
                    raise fbe.TemporaryFeedbackError("Sort value must be an int")
                
                value: T = elem[0]
            else:
                if not simple:
                    raise fbe.TemporaryFeedbackError("All elems but be either a list or not")
                
                value: T = elem
                sort_value = i

            if not isinstance(value, value_type.value):
                raise fbe.TemporaryFeedbackError("Type of value must be the given value_type")
        
            if isinstance(vc_tmp, dict):
                vc_tmp
            
            # TODO check tree recursively
                

        return Attribute(
            community,
            name,
            alias,
            value_type.value,  
            "tmp",
            min_value_slots,
            max_value_slots,
            unique_slots,
            unique_values_per_list,
            user_bound
        )

    def _normalize_and_validate_syn(self, syn: str) -> str:
        syn = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, '_', syn.strip().casefold())

        if not syn:
            raise fbe.TemporaryFeedbackError
        
        if len(syn) > Attribute.MAX_SYN_LEN:
            raise fbe.TemporaryFeedbackError
        
        if syn in Attribute.LOOKUP.setdefault(self._community, {}):
            raise fbe.TemporaryFeedbackError
        
        illegal_chars: set[str] = set()

        for char in syn:
            if char not in _VALID_SYN_CHARS:
                illegal_chars.add(char)

        if illegal_chars:
            raise fbe.TemporaryFeedbackError(illegal_chars)
        
        return syn
    
    def _normalize_and_implement_value(self, value: tuple[T, int]) -> T:
        unnormalized, sort_value = value

        if not isinstance(value, self._value_type):
            raise TypeError
        
        if sort_value > Attribute.NUMBER_MAX:
            raise fbe.TemporaryFeedbackError
        
        normalized = self.normalize(unnormalized)

        self._sort_value[normalized] = sort_value
        
        prev_unnormalized = self._unnormalize.get(normalized, None)

        if prev_unnormalized is None:
            self._unnormalize[normalized] = unnormalized
        else: 
            raise fbe.TemporaryFeedbackError()
        
        return normalized
    

    # --- Methods ---

    def _from_str_singular(self, s: str) -> T:
        match self._value_type:
            case builtins.bool:
                s = s.lower()

                if s in "false":
                    result = False
                elif s == "true":
                    result = True
                else:
                    raise fbe.NotAProperValue("boolean", s)

            case builtins.int:
                if len(s) > Attribute.INT_PART_MAX_LEN:
                    raise fbe.OutsideOfValidRange(s, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)

                try:
                    result = int(s)
                except Exception:
                    raise fbe.NotAProperValue("integer", s)

                if not (Attribute.NUMBER_MIN < result < Attribute.NUMBER_MAX):
                    raise fbe.OutsideOfValidRange(result, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
                
            case decimal.Decimal:
                if len(s) > Attribute.DECIMAL_MAX_LEN:
                    raise fbe.OutsideOfValidRange(s, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
                
                try:
                    result = Decimal(s)
                    result = result.quantize(Decimal(f"1E-{Attribute.DEC_PART_MAX_LEN}"))
                except Exception:
                    raise fbe.NotAProperValue("decimal", s)
                
                if not (Attribute.NUMBER_MIN < result < Attribute.NUMBER_MAX):
                    raise fbe.OutsideOfValidRange(result, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
            
            case dt.time | dt.date | dt.datetime:
                # If a date is in the type
                if issubclass(self._value_type, (dt.date, dt.datetime)):
                    s = re.sub(_DATE_ALTERNATIVE_DELIMITERS_PATTERN, "-", s)
                
                try:
                    result = self._value_type.fromisoformat(s)
                except Exception:
                    raise fbe.TemporaryFeedbackError("Invalid datetime repr")
                
                if isinstance(result, (dt.time, dt.datetime)):
                    if result.tzinfo is None:
                        result = result.replace(tzinfo=dt.timezone.utc)

            case dt.timedelta:
                result = _parse_timedelta(s)

            case builtins.str:
                if len(s) > Attribute.STR_MAX_LEN:
                    raise fbe.TooLongValue("string", s, Attribute.STR_MAX_LEN)
                
                result = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, " ", s)
        
            case _:
                raise TypeError("Type was forgotten to be added here")
        
        return result  # type: ignore
    
    def from_str(self, s: str, keep_normalized: bool) -> list[T]:
        if not (s := s.strip()):
            return []
        
        try:
            v: str | list[str] = json.loads(s)
        except json.JSONDecodeError:
            raise fbe.TemporaryFeedbackError

        if isinstance(v, str):
            v = [v]
        elif isinstance(v, list):
            if not v:
                return []
            
            for elem in v:
                if not isinstance(elem, str):
                    raise fbe.TemporaryFeedbackError
        else:
            raise fbe.TemporaryFeedbackError
        
        converted: list[T] = [self._from_str_singular(elem) for elem in v]

        if self.collection:
            # Normalize to lookup, unnormalize to get correct version
            to_collection = []
            
            for elem in converted:
                try:
                    normalized = self.normalize(elem)

                    if keep_normalized:
                        if normalized not in self._unnormalize:
                            raise KeyError
                        
                        to_collection.append(normalized)
                    else:
                        to_collection.append(self._unnormalize[normalized])
                except KeyError:
                    raise fbe.TemporaryFeedbackError("Not a valid collection value")
                
            return to_collection
        
        return converted

    @functools.lru_cache()
    def normalize(self, unnormalized: T) -> T:
        if isinstance(unnormalized, str):
            normalized: T = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, " ", unnormalized.strip().casefold())  # type: ignore
        else:
            normalized = unnormalized
        
        return normalized

    @staticmethod
    def _sort_key_anything_time(value: dt.time | dt.date | dt.datetime | dt.timedelta) -> float:
        if isinstance(value, dt.time):
            return (
                value.microsecond +
                value.second *   1_000_000 +
                value.minute *  60_000_000 +
                value.hour * 3_600_000_000
            )
        
        elif isinstance(value, dt.datetime):
            return value.timestamp()
         
        elif isinstance(value, dt.date):
            return value.timetuple().tm_yday
        
        elif isinstance(value, dt.timedelta):
            return value.total_seconds()
        
        raise TypeError

    def _sort_key_singular(self, value: Opt[T], sign: Literal[+1, -1]):
        if issubclass(self._value_type, bool):
            if value is None:
                return 2 * sign
            
            return int(value) * sign  # type: ignore
            
        if issubclass(self._value_type, (int, Decimal)):
            if value is None:
                return Attribute.SORT_KEY_LAST_NUMBER * sign
            
            return value * sign  # type: ignore
        
        if issubclass(self._value_type, (dt.time, dt.date, dt.datetime, dt.timedelta)):
            if value is None:
                return (Attribute._sort_key_anything_time(self._value_type.max) + 1) * sign
            
            return Attribute._sort_key_anything_time(value) * sign  # type: ignore

    def sort_key(self, value: str, sign: Literal[+1, -1]) -> tuple[int, ...] | Any:
        values = self.from_str(value, True)
        
        if not values:
            return Attribute.SORT_KEY_LAST_NUMBER + 1
        
        if self.collection:
            try:
                return tuple(
                    self._sort_value[elem] * sign for elem in values
                )
            except KeyError as e:
                raise RuntimeError(
                    f"Sort value for elem '{e.args[0]}' not found, which " +
                    f"should not happen. {self._sort_value=}"
                )
        
        return tuple(self._sort_key_singular(value, sign) for value in values)

    @property
    def collection(self) -> bool:
        return self._list is not None or self._tree is not None

    @property
    def required(self) -> bool:
        return self._min_value_slots > 0
    
    def is_empty(self, value: str) -> bool:
        return bool(self.from_str(value, True)) 

    def value_to_memory(self, value: T) -> int:
        if isinstance(value, str):
            return len(value)
        if isinstance(value, int):
            return 8
        if isinstance(value, float):
            return 8
        if isinstance(value, dt.time):
            return 8
        if isinstance(value, dt.datetime):
            return 8
        if isinstance(value, dt.timedelta):
            return 8
        
        raise TypeError  
    

def module_integrity():
    if AttributeValueTypeT.__value__.__args__ != tuple(vt.value for vt in AttributeValueTypeEnum):
        raise RuntimeError("Enum does not equal type!!")
    
module_integrity()