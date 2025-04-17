from dataclasses import dataclass, field
import enum
import datetime as dt
import functools
import json
from threading import Lock, RLock
from typing import Any, ClassVar, Iterable, Literal, NamedTuple, NotRequired, Optional as Opt, Self, Sequence, TypedDict
import typing
from database import queries
from discordtools import feedbackerrors as fbe
import re
from structures.community import Community
import builtins
from collections2.range import Range
from decimal import Decimal
import decimal
from structures.list import List
from utils import text, timetools, jsonutils


#------#   Module Constants, Types & Helper Functions   #------#

type AttrT = 'Attribute'


# --- Attribute Value Type --- #

type AttributeValueTypeT = (
    bool | int | Decimal | 
    dt.time | dt.date | dt.datetime | dt.timedelta | 
    str
)

type_ = type

@dataclass(frozen=True)
class AttributeValueType[T: AttributeValueTypeT]:
    id: int
    name: str
    type: type[T]

    _attribute_value_types: ClassVar[list[Self]] = field(init=False, default_factory=list)
    _attribute_value_type_id_lookup: ClassVar[dict[int, Self]] = field(init=False, default_factory=dict)
    _attribute_value_type_name_lookup: ClassVar[dict[str, Self]] = field(init=False, default_factory=dict)
    _attribute_value_type_type_lookup: ClassVar[dict[str, Self]] = field(init=False, default_factory=dict)

    def __hash__(self):
        return hash((self.id, self.name, self.type.__qualname__))
    
    def __post_init__(self):
        for elem in AttributeValueType._attribute_value_types:
            if self.name == elem.name or self.id == elem.id or self.type == elem.type:
                raise RuntimeError()
            
        AttributeValueType._attribute_value_types.append(self)
        AttributeValueType._attribute_value_type_id_lookup[self.id] = self
        AttributeValueType._attribute_value_type_name_lookup[self.name] = self
        AttributeValueType._attribute_value_type_type_lookup[self.type.__qualname__] = self

    @classmethod
    def lookup_by_id(cls, id: int) -> Self:
        try:
            return cls._attribute_value_type_id_lookup[id]
        except KeyError as e:
            raise LookupError(*e.args)
        
    @classmethod
    def lookup_by_name(cls, name: str) -> Self:
        try:
            return cls._attribute_value_type_name_lookup[name]
        except KeyError as e:
            raise LookupError(*e.args)
        
    @classmethod
    def lookup_by_type(cls, type: type_[T]) -> 'AttributeValueType[T]':
        try:
            return cls._attribute_value_type_type_lookup[type.__qualname__]
        except KeyError as e:
            raise LookupError(*e.args)

AttributeValueType(1, 'boolean', bool)
AttributeValueType(2, 'integer', int)
AttributeValueType(3, 'decimal', Decimal)
AttributeValueType(4, 'time', dt.time)
AttributeValueType(5, 'date', dt.date)
AttributeValueType(6, 'date_and_time', dt.datetime)
AttributeValueType(7, 'timespan', dt.timedelta)
AttributeValueType(8, 'text', str)

AttributeValueTypeEnum = enum.Enum(
    'AttributeValueTypeEnum', {avt.name: avt for avt in AttributeValueType._attribute_value_types}
)

# --- Collection Types --- #

class UserCollectionListItemT(TypedDict, total=True):
    value: str
    sort_value: int
type UserCollectionListT = list[UserCollectionListItemT]

@dataclass(frozen=True)
class CollectionListItem[T]:
    value: T
    display_value: T
    sort_value: int
type CollectionListT[T] = list[CollectionListItem[T]]


class UserCollectionTreeItemT(TypedDict, total=True):
    value: str
    sort_value: int
    children: NotRequired[list['UserCollectionTreeItemT']]
type UserCollectionTreeT = list[UserCollectionTreeItemT]

@dataclass(frozen=True)
class CollectionTreeItem[T]:
    value: T
    display_value: T
    sort_value: int
    nodes: 'CollectionTreeT[T]'
type CollectionTreeT[T] = list[CollectionTreeItem[T]]


type UserCollectionT = None | UserCollectionListT | UserCollectionTreeT
type CollectionT[T] = None | CollectionListT[T] | CollectionTreeT[T]


class AttributeTableT[T](TypedDict):
    id: int
    list_id: int
    name: str
    display_name: str
    sort_value: int
    alias: list[str]
    value_type: int
    value_collection: bytes
    min_value_slots: int
    max_value_slots: int
    unique_slots: bool
    user_bound: bool
    unique_in_list: bool

_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')
    

#------#   Attribute   #------#	

@dataclass(frozen=True)
class Attribute[T: AttributeValueTypeT]:
    """Represent an attribute of a Trickjump.

    In a relational database model 'Trickjump' would represent a table,
    'Attribute' a column and specific values interacting with the
    'Attribute' class would be rows.

    Instead of specific types, values are passed in mostly as str, None
    or other basic data types, which are especially supported by discord.py.
    """

    list_: List
    id: int 
    name: str
    display_name: str
    sort_value: int
    alias: set[str]
    value_type: AttributeValueType
    value_collection: CollectionT
    min_value_slots: int
    max_value_slots: int
    unique_slots: bool
    user_bound: bool
    unique_in_list: bool

    # --- CONSTANTS ---

    # int | decimal
    NUMBER_MAX: ClassVar[int] = 2 ** 63 - 1
    NUMBER_MIN: ClassVar[int] = -NUMBER_MAX - 1
    DECIMAL_PRECISION: ClassVar[int] = decimal.getcontext().prec
    INT_PART_MAX_LEN: ClassVar[int] = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
    DEC_PART_MAX_LEN: ClassVar[int] = DECIMAL_PRECISION - INT_PART_MAX_LEN
    DECIMAL_MAX_LEN: ClassVar[int] = DECIMAL_PRECISION if DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1
    
    # str
    STR_MAX_LEN: ClassVar[int] = 512

    # Collection
    COLLECTION_MAX_MEMORY: ClassVar[int] = 1024 * 32
    COLLECTION_MAX_ELEMS: ClassVar[int] = 1024

    MAX_DEPTH: ClassVar[int] = 64
    
    # General
    MAX_SYN_LEN: ClassVar[int] = 32
    MAX_ALIASES: ClassVar[int] = 31
    MAX_ATTRIBUTES_PER_COMMUNITY: ClassVar[int] = 50
    MAX_VALUE_SLOTS: ClassVar[int] = 32

    TABLE_NAME: ClassVar[str] = "attribute"
    SORT_KEY_LAST_NUMBER: ClassVar[int] = max(abs(NUMBER_MIN), abs(NUMBER_MAX)) + 1

    # --- Methods ---

    @property
    def syns(self) -> set[str]:
        return {self.name} | self.alias
    
    @classmethod
    def _check_generic_number_valid(cls, number: int | float | Decimal) -> None:
        if not (Attribute.NUMBER_MIN < number < Attribute.NUMBER_MAX):
            raise fbe.OutsideOfValidRange(number, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
        
    @classmethod
    def _parse_str_singular(cls, s: str, value_type: AttributeValueType[T]) -> T:
        if not isinstance(s, str):
            raise fbe.TemporaryFeedbackError("Not a string")
        
        match value_type:
            case builtins.bool:
                s = s.lower()

                if s in "false":
                    result = False
                elif s == "true":
                    result = True
                else:
                    raise fbe.NotAProperValue("boolean", s)

            case builtins.int:
                try:
                    result = int(s)
                except Exception:
                    raise fbe.NotAProperValue("integer", s)
                
                cls._check_generic_number_valid(result)
    
            case decimal.Decimal:
                try:
                    result = Decimal(s)
                    result = result.quantize(Decimal(f"1E-{Attribute.DEC_PART_MAX_LEN}"))
                except Exception:
                    raise fbe.NotAProperValue("decimal", s)
                
                cls._check_generic_number_valid(result)
            
            case dt.time | dt.date | dt.datetime:
                # If a date is in the type
                if issubclass(value_type, (dt.date, dt.datetime)):
                    s = re.sub(_DATE_ALTERNATIVE_DELIMITERS_PATTERN, "-", s)
                
                try:
                    result = value_type.fromisoformat(s)
                except Exception:
                    raise fbe.TemporaryFeedbackError("Invalid datetime repr")
                
                if isinstance(result, (dt.time, dt.datetime)):
                    if result.tzinfo is None:
                        result = result.replace(tzinfo=dt.timezone.utc)

            case dt.timedelta:
                result = timetools.parse_timedelta(s)

            case builtins.str:
                if len(s) > Attribute.STR_MAX_LEN:
                    raise fbe.TooLongValue("string", s, Attribute.STR_MAX_LEN)
                
                result = text.fix_whitespace(s, " ", True)
                
            case _:
                raise TypeError("Type was forgotten to be added here")
        
        return result  # type: ignore
    
    def parse_str(self, s: str, keep_normalized: bool, value_type: Opt[AttributeValueType] = None) -> list[T]:
        if not (s := s.strip()):
            return []
        
        try:
            v: str | list[str] = jsonutils.json_loads_safe(s, 1)
        except (json.JSONDecodeError, RecursionError):
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
        
        value_type = value_type or self.value_type

        converted: list[T] = [self._parse_str_singular(elem, value_type) for elem in v]

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
            normalized: T = text.fix_whitespace(unnormalized.lower(), " ", True)  # type: ignore
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
        if issubclass(self.value_type.type, bool):
            if value is None:
                return 2 * sign
            
            return int(value) * sign  # type: ignore
            
        if issubclass(self.value_type.type, (int, Decimal)):
            if value is None:
                return Attribute.SORT_KEY_LAST_NUMBER * sign
            
            return value * sign  # type: ignore
        
        if issubclass(self.value_type.type, (dt.time, dt.date, dt.datetime, dt.timedelta)):
            if value is None:
                return (Attribute._sort_key_anything_time(self.value_type.type.max) + 1) * sign
            
            return Attribute._sort_key_anything_time(value) * sign  # type: ignore

    def sort_key(self, value: str, sign: Literal[+1, -1]) -> tuple[int, ...] | Any:
        values = self.parse_str(value, True)
        
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
        return self._collection_list is not None or self._collection_tree is not None

    @property
    def required(self) -> bool:
        return self._min_value_slots > 0
    
    def is_empty(self, value: str) -> bool:
        return bool(self.parse_str(value, True)) 

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