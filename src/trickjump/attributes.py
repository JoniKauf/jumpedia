

import ast
from collections import Counter, defaultdict
import itertools
from trickjump.context import Context
import datetime as dt
import functools
import json
import sys
from threading import Lock
from typing import Any, Callable, Hashable, Iterable, Literal, Optional as Opt, Self, Sequence, TypeVar, cast
from enum import Enum, auto
from discordtools import errors, feedbackerrors as fbe
from people.person import Person
import re
from collections2 import tree
from trickjump.community import Community
import builtins
from collections2.range import Range
from decimal import Decimal
import decimal
import string

type AttrT = 'Attribute'
type AttributeValueTypeT = (
    bool | int | Decimal | 
    dt.time | dt.date | dt.datetime | dt.timedelta | 
    str
)


#------#   Module Constants & Helper Functions   #------#

_NAME_CONVERSION_PATTERN = re.compile(r'(?!^)([A-Z]+)')
_ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r'\s+')
_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'/\.')
_VALID_SYN_CHARS: set[str] = set('abcdefghijklmnopqrstuvwxyz_0123456789')

_TIMEDELTA_PARSE_PATTERN = re.compile(r'''
    ^                     # String start
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
        (h|hrs?|hours?)        # [Group 5: 'h', 'hr', 'hrs', 'hour' or 'hours']
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
            (?:\.[0-9]*)?         # followed by optional: '.' followed by any digits 0 to ∞ times
        )                     # ]
        \s*                   # Whitespace 0 to ∞ times
        (s|secs?|seconds?)    # [Group 9: 's', 'sec', 'secs', 'second' or 'seconds']
    )?                    # End group, its insides must either fully match or not exist at all
    $                     # String end
''', re.VERBOSE | re.IGNORECASE)

def _parse_timedelta(s: str) -> dt.timedelta:
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
        unit = groups[i].lower()[0]
        value = Decimal(groups[i + 1])

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
        raise ValueError("Number too small or big")

def _get_plural_from_str_method[TParent](
    singular_from_str: Callable[[Any, Opt[str]], Opt[TParent]]
) -> Callable[[Any, Opt[str]], Opt[list[TParent]]]:

    def _from_str(self, value: Opt[str]) -> Opt[list[TParent]]:
        if value is None or not (value := value.strip()):
            return None

        v: list[str] = json.loads(value)

        if not isinstance(v, list):
            raise Exception
        
        if self.max > 0 and len(v) > self.max:
            raise Exception
        
        counter: Counter[TParent] = Counter()
        unfiltered_v = v
        filtered_v: list[TParent] = []

        for elem in unfiltered_v:
            if not isinstance(elem, str):
                raise Exception
            
            elem = singular_from_str(self, elem)
            
            if elem is None:
                continue
                
            if elem not in counter:
                counter[elem] = 1
            else:
                counter[elem] += 1

            if counter[elem] > self.max_duplicates:
                raise fbe.TemporaryFeedbackError

            filtered_v.append(elem)

        return filtered_v or None
    
    return _from_str


class ValueCollectionType(Enum):
    NONE = auto()
    LIST = auto()
    TREE = auto()

#------#   Attribute   #------#	

class Attribute[T: AttributeValueTypeT]:
    TYPE_ID: int
    MAX_SYN_LEN = 32
    MAX_ATTRIBUTES_PER_COMMUNITY = 50
    
    LOOKUP: dict[Community, dict[str, 'Attribute']] = {}

    # int | decimal
    NUMBER_MAX: int = 2 ** 63 - 1
    NUMBER_MIN: int = -NUMBER_MAX - 1
    DECIMAL_PRECISION: int = decimal.getcontext().prec
    INT_PART_MAX_LEN: int = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
    DEC_PART_MAX_LEN: int = DECIMAL_PRECISION - INT_PART_MAX_LEN
    DECIMAL_MAX_LEN: int = DECIMAL_PRECISION if DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1
 
    # str
    STR_MAX_LEN = 1024

    # Collection
    COLLECTION_MAX_MEMORY = 1024 * 32
    COLLECTION_MAX_ELEMS = 1024

    MAX_DEPTH = 64

    LOCK = Lock()

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
        with Attribute.LOCK:
            self.community = community

            self.name = self._normalize_and_validate_syn(name)
            self.alias = set(self._normalize_and_validate_syn(a) for a in alias)

            if self.value_type not in AttributeValueTypeT.__value__.__args__:
                raise TypeError
            
            self.value_type = value_type

            self.list: Opt[None | list[T]] = None
            self.tree: Opt[tree.Tree] = None

            self.sort_value: dict[T, int] = {}
            self.unnormalize = {}

            if not value_collection:
                pass
            elif isinstance(value_collection, Sequence):
                self.list = []

                for value in value_collection:
                    v_norm = self._normalize_and_implement(value)
                    self.list.append(v_norm)
                    
                if len(self.list) > Attribute.COLLECTION_MAX_ELEMS:
                    raise fbe.TemporaryFeedbackError
                
                if sum(self.value_to_memory(v) for v in self.list) > Attribute.COLLECTION_MAX_MEMORY:
                    raise fbe.TemporaryFeedbackError
            else:
                try:
                    self.tree = tree.Tree(
                        value_collection, 
                        self._normalize_and_implement, 
                        Attribute.MAX_DEPTH, 
                        Attribute.COLLECTION_MAX_ELEMS, 
                        Attribute.NUMBER_MAX
                    )
                except tree.TreeError as e:
                    raise fbe.TemporaryFeedbackError(e)
                
                if sum(
                    self.value_to_memory(n.value) 
                    for n in self.tree._node_lookup.values()
                ) > Attribute.COLLECTION_MAX_MEMORY:
                    raise fbe.TemporaryFeedbackError

            if min_value_slots < 0:
                raise fbe.TemporaryFeedbackError
            
            if max_value_slots < 1 or max_value_slots < min_value_slots:
                raise fbe.TemporaryFeedbackError
            
            self.min_value_slots = min_value_slots
            self.max_value_slots = max_value_slots

            self.unique_slots = unique_slots

            if unique_values_per_list and user_bound:
                raise fbe.TemporaryFeedbackError("dont work together")
            
            self.unique_value_per_list = unique_values_per_list
            self.user_bound = user_bound

            lookup = Attribute.LOOKUP.setdefault(community, {})

            for syn in (name, *alias):
                lookup[syn] = self
                
            # TODO:
            # - Add to database

    def _normalize_and_validate_syn(self, syn: str) -> str:
        syn = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, '_', syn.strip().casefold())

        if not syn:
            raise fbe.TemporaryFeedbackError
        
        if len(syn) > Attribute.MAX_SYN_LEN:
            raise fbe.TemporaryFeedbackError
        
        if syn in Attribute.LOOKUP.setdefault(self.community, {}):
            raise fbe.TemporaryFeedbackError
        
        illegal_chars: set[str] = set()

        for char in syn:
            if char not in _VALID_SYN_CHARS:
                illegal_chars.add(char)

        if illegal_chars:
            raise fbe.TemporaryFeedbackError(illegal_chars)
        
        return syn
    
    def _normalize_and_implement(self, value: tuple[T, int]) -> T:
        unnormalized, sort_value = value

        if isinstance(value, self.value_type):
            raise TypeError
        
        normalized = self.normalize(unnormalized)

        self.sort_value[normalized] = sort_value
        
        prev_unnormalized = self.unnormalize.get(normalized, None)

        if prev_unnormalized is None:
            self.unnormalize[normalized] = unnormalized
        else: 
            raise fbe.TemporaryFeedbackError()
        
        return normalized
    
    def _from_str_singular[T1: AttributeValueTypeT](self, context: Context, value: str, value_type: Opt[type[T1]] = None) -> T1:
        if value_type is None:
            value_type = self.value_type  # type: ignore
            
        match value_type:
            case builtins.bool:
                value = value.lower()

                if value in "false":
                    result = False
                elif value == "true":
                    result = True
                else:
                    raise fbe.NotAProperValue("boolean", value)
                
            case builtins.int:
                if len(value) > Attribute.INT_PART_MAX_LEN:
                    raise fbe.OutsideOfValidRange(value, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)

                try:
                    result = int(value)
                except Exception:
                    raise fbe.NotAProperValue("integer", value)

                if not (Attribute.NUMBER_MIN < result < Attribute.NUMBER_MAX):
                    raise fbe.OutsideOfValidRange(result, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
                
            case decimal.Decimal:
                if len(value) > Attribute.DECIMAL_MAX_LEN:
                    raise fbe.OutsideOfValidRange(value, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
                
                try:
                    result = Decimal(value)
                    result = result.quantize(Decimal(f"1E-{Attribute.DEC_PART_MAX_LEN}"))
                except Exception:
                    raise fbe.NotAProperValue("decimal", value)
                
                if not (Attribute.NUMBER_MIN < result < Attribute.NUMBER_MAX):
                    raise fbe.OutsideOfValidRange(result, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
            
            case dt.time | dt.date | dt.datetime:
                # If a date is in the type
                if issubclass(value_type, (dt.date, dt.datetime)):
                    value = re.sub(_DATE_ALTERNATIVE_DELIMITERS_PATTERN, "-", value)
                
                try:
                    result = value_type.fromisoformat(value)
                except Exception:
                    raise fbe.TemporaryFeedbackError("Invalid datetime repr")
                
                if isinstance(result, (dt.time, dt.datetime)):
                    if result.tzinfo is None:
                        result = result.replace(tzinfo=dt.timezone.utc)

            case dt.timedelta:
                parts = value.split(" ")

                for part in parts:
                    pass
            case builtins.str:
                if len(value) > Attribute.STR_MAX_LEN:
                    raise fbe.TooLongValue("string", value, Attribute.STR_MAX_LEN)
                
                result = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, " ", value)

            case _:
                raise ValueError
        
        return result

    def normalize(self, unnormalized: T) -> T:
        if isinstance(unnormalized, str):
            normalized: T = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, " ", unnormalized.strip().casefold())  # type: ignore
        else:
            normalized = unnormalized
        
        return normalized
    
    def value_to_memory(self, value: T) -> int:
        if isinstance(value, str):
            return len(value)
        if isinstance(value, int):
            return 8
        if isinstance(value, float):
            return 8
        if isinstance(value, time):
            return 4
        if isinstance(value, datetime):
            return 8
        if isinstance(value, timedelta):
            return 8
        
        raise TypeError

    def is_empty(self, value: Opt[str]) -> bool:
        return self.from_str(value) is None
            
    def from_str(self, s: Opt[str]) -> Opt[T]:
        if s is None or not (s := s.strip()):
            return None
        
        try:
            loaded: Any = json.loads(s)
        except json.JSONDecodeError:
            raise fbe.TemporaryFeedbackError
        
        # if isinstance(loaded, )
        # elif isinstance(loaded, list):
        #     values: list[T] = []
        results: list[T]
        match self.value_type:
            case builtins.bool:
                value = value.lower()

                if value == "false":
                    res = False
                elif value == "true":
                    res = True
                else:
                    raise fbe.NotAProperValue("boolean", value)
            case builtins.int | builtins.float:
                if len(value) > Attribute.NUMBER_MAX_LEN_AS_STR:
                    raise fbe.OutsideOfValidRange(value, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)

                try:
                    res = self.value_type(value)
                except ValueError:
                    raise fbe.NotAProperValue("number", value)

                if not (Attribute.NUMBER_MIN < res < Attribute.NUMBER_MAX):
                    raise fbe.OutsideOfValidRange(res, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
            case builtins.str:
                if len(value) > Attribute.STR_MAX_LEN:
                    raise fbe.TooLongValue("string", value, Attribute.STR_MAX_LEN)
                
                res = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, " ", value)
            case _:
                raise ValueError

        return res  # type: ignore
            
    
            
    
            
        
    

# #------#   Attribute Specific Implementations   #------#

# class AttributeBool(Attribute[bool]):
#     TYPE_ID = 1

#     def _from_str(self, value: Opt[str]) -> Opt[bool]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         value = value.lower()

#         if value == "true":
#             return True
#         if value == "false":
#             return False
        
#         raise fbe.NotAProperValue("boolean", value)
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return 2 * sign
        
#         return (not v) * sign
    

# class AttributeInt(Attribute[int]):
#     TYPE_ID = 2

    

#     def _from_str(self, value: Opt[str]) -> Opt[int]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         if len(value) > Attribute.NUMBER_MAX_LEN_AS_STR:
#             raise fbe.OutsideOfValidRange(
#                 value, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX
#             )
        
#         try:
#             result = int(value)
#         except ValueError:
#             raise fbe.NotAProperValue("integer", value)

#         if not (Attribute.NUMBER_MIN < result < Attribute.NUMBER_MAX):
#             raise fbe.OutsideOfValidRange(
#                 result, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX
#             )
        
#         return result

#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             v = Attribute.NUMBER_MAX + 1
            
#         return v * sign
    

# class AttributeStr(Attribute[str]):
#     TYPE_ID = 3

#     MAX_STR_LEN = 2 ** 10

#     def _from_str(self, value: Opt[str]) -> Opt[str]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         if len(value) > Attribute.MAX_STR_LEN:
#             raise fbe.TooLongValue("string", value, Attribute.MAX_STR_LEN)
        
#         return value

#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return ((sys.maxunicode + 1) * sign,)
        
#         if not case_sensitive:
#             v = v.casefold()

#         return tuple(ord(char) * sign for char in v)


# class AttributeStrCollection(AttributeStr):
#     TYPE_ID = 4

#     MAX_COLLECTION_LEN = 2 ** 12

#     def __init__(
#         self, 
#         context: ContextT,
#         name: str, 
#         alias: Iterable[str], 
#         required: bool,
#         unique: bool,
#         hidden: bool, 
#         *args: *tuple[Sequence[str]]
#     ):
#         collection, = args             

#         super().__init__(
#             context=context,
#             name=name, 
#             alias=alias, 
#             required=required,
#             unique_in_list=unique,
#             interactability=hidden
#         )

#         # dict[casefolded_val, tuple[val, index]]
#         self._collection: dict[str, tuple[str, int]] = {}

#         if len(collection) > Attribute.MAX_COLLECTION_LEN:
#             raise fbe.TooManyCollectionElements(
#                 self.name, Attribute.MAX_COLLECTION_LEN
#             )
        
#         for i, elem in enumerate(collection):
#             elem = elem.strip()
#             elem_cf = elem.casefold()
            
#             if elem_cf in collection:
#                 raise fbe.CollectionElementCollision(self.name, elem_cf)
            
#             self._collection[elem_cf] = (elem, i)

#     @property
#     def collection(self) -> dict[str, tuple[str, int]]:
#         return self._collection
    
#     def _from_str(self, value: Opt[str]) -> Opt[str]:
#         v = super()._from_str(value)

#         if v is None:
#             return None
        
#         if v not in self.collection:
#             raise fbe.NotPartOfTheCollection(self.name, v)
        
#         return v.casefold()
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return len(self.collection) * sign
        
#         return self.collection[v][1] * sign
    
# class AttributeStrCollectionTree(Attribute[str]):
#     def __init__(
#         self, 
#         context: str, 
#         name: str, 
#         alias: Iterable[str], 
#         required: bool, 
#         unique: bool, 
#         hidden: bool, 
#         normalize: Callable[[str], str],
#         tree: TreeT[str]
#     ):
#         self.tree = tree_.Tree(tree, normalize)

#         super().__init__(
#             context, 
#             name, 
#             alias, 
#             required, 
#             unique, 
#             hidden
#         )



# class AttributePerson(Attribute[Person]):
#     TYPE_ID = 5
#     MAX_PERSON_NAME_LEN = Person.MAX_PERSON_NAME_LEN

#     def _from_str(self, value: Opt[str]) -> Opt[Person]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         return Person.get(value)
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return ((sys.maxunicode + 1) * sign,)
        
#         name: str = v.name if case_sensitive else v.name.casefold()

#         return tuple(ord(char) * sign for char in name)


# #------#   Attribute Plural Implementations   #------#

# ATTRIBUTE_PLURAL_BASE_ID = 128

# class AttributePluralStr(AttributeStr, _AttributePluralMixin[str]):
#     TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributeStr.TYPE_ID

#     def __init__(
#         self, 
#         context: ContextT,
#         name: str, 
#         alias: Iterable[str], 
#         required: bool,
#         unique: bool,
#         hidden: bool, 
#         *other: *tuple[int, int]
#     ):
#         max, max_duplicates = other

#         super().__init__(
#             context=context,
#             name=name, 
#             alias=alias, 
#             required=required,
#             unique_in_list=unique,
#             interactability=hidden 
#         )

#         _AttributePluralMixin.__init__(
#             self,
#             max=max,
#             max_duplicates=max_duplicates
#         )
    
#     _from_str: Callable[[Opt[str]], Opt[list[str]]] = _get_plural_from_str_method(AttributeStr._from_str)  # type: ignore
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return (((sys.maxunicode + 1) * sign,),)
        
#         return tuple(
#             tuple(ord(char) * sign for char in (
#                 s if case_sensitive else s.casefold()
#             )) 
#             for s in v
#         )

# class AttributePluralStrCollection(AttributeStrCollection, _AttributePluralMixin[str]):
#     TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributeStrCollection.TYPE_ID

#     def __init__(
#         self, 
#         context: ContextT,
#         name: str, 
#         alias: Iterable[str], 
#         required: bool, 
#         unique: bool,
#         hidden: bool,
#         *other: *tuple[int, int, Sequence[str]]
#     ):
#         max, max_duplicates, collection = other

#         super().__init__(
#             context,
#             name,
#             alias,
#             required,
#             unique,
#             hidden,
#             *(collection,)
#         )

#         _AttributePluralMixin.__init__(
#             self, 
#             max=max,
#             max_duplicates=max_duplicates
#         )

#     _from_str: Callable[[Opt[str]], Opt[list[str]]] = _get_plural_from_str_method(AttributeStrCollection._from_str)  # type: ignore
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return (len(self.collection) * sign,)
        
#         return tuple(
#             self.collection[elem][1] for elem in v
#         )
    

# class AttributePluralPerson(AttributePerson, _AttributePluralMixin[Person]):
#     TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributePerson.TYPE_ID
    
#     def __init__(
#         self, 
#         context: ContextT, 
#         name: str, 
#         alias: Iterable[str], 
#         required: bool,
#         unique: bool,
#         hidden: bool,
#         *other: *tuple[int, int]
#     ):
#         max, max_duplicates = other

#         super().__init__(
#             context=context, 
#             name=name, 
#             alias=alias, 
#             required=required,
#             unique_in_list=unique,
#             interactability=hidden
#         )

#         _AttributePluralMixin.__init__(
#             self, 
#             max=max,
#             max_duplicates=max_duplicates
#         )

#     _from_str: Callable[[Opt[str]], Opt[list[Person]]] = _get_plural_from_str_method(AttributePerson._from_str)  # type: ignore
     
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return (((sys.maxunicode + 1) * sign,),)
        
#         return tuple(
#             tuple(ord(char) * sign for char in (
#                 person.name if case_sensitive else person.name.casefold()
#             )) 
#             for person in v
#         )


#------#   Module Functionality   #------#

def get(context: Context, attr: str) -> Attribute:
    try:
        lookup = Attribute.LOOKUP[context.community]
    except KeyError:
        raise fbe.TemporaryFeedbackError
    
    try:
        return lookup[attr]
    except KeyError:
        raise fbe.InvalidAttribute(attr)

def get_all(context: Context) -> tuple[Attribute, ...]:
    return tuple(Attribute.LOOKUP[context.community].values())
    

if __name__ == '__main__':
    def debug_print(attr: Attribute):
        print("\n\n" + "\n".join(f"{k} = {v!r}" for k, v in attr.__dict__.items() if not k.startswith("__")))
    
    attr_name = Attribute(Community(), "difficulty", ["diff", "d"], str, [("0/10", 0), ("0.5/10", 1), ("1/10", 2)], 0, 1, True, True, False)
    attr_count = Attribute(Community(), "count", ["c"], int, [(1, 1), (2, 2), (3, 3)], 1, 1, True, True, False)
    debug_print(attr_name)
    debug_print(attr_count)
    
    # attr = AttributePluralStr(TMP_CTX, "test", ["test"], True, True, True, 10, 100)
    # print(attr._from_str(f'[""]'))



#hello schatz i love you

# def _tree_worker[T: Hashable](tree: TreeT[T], normalize: Callable[[T], T]) -> tuple[dict[T, set[T]], dict[T, T]]:
#     children: dict[T, set[T]] = {}
#     unnormalize: dict[T, T] = {}
#     all_visited: set[T] = set()

#     def _visit_node(node_names: tuple[T, T], child_nodes: TreeT[T], depth: int):
#         if depth > _RECURSION_LIMIT:
#             raise fbe.TemporaryFeedbackError

#         node_name, norm_node_name = node_names
        
#         # Check if duplicate node, otherwise add to collection 
#         if norm_node_name in all_visited:
#             raise fbe.TemporaryFeedbackError("Cyclic")
        
#         all_visited.add(norm_node_name)
        
#         unnormalize[norm_node_name] = node_name

#         for child_node_name, child_child_nodes in child_nodes.items():
#             norm_child_node_name = normalize(child_node_name)
                
#             children.setdefault(norm_node_name, set()).add(norm_child_node_name)
            
#             _visit_node(
#                 (child_node_name, norm_child_node_name), 
#                 child_child_nodes, 
#                 depth + 1
#             )

#     for child_node_name, child_child_nodes in tree.items():
#         norm_child_node_name = normalize(child_node_name)

#         _visit_node(
#             (child_node_name, norm_child_node_name), 
#             child_child_nodes, 
#             1
#         )

#     return children, unnormalize