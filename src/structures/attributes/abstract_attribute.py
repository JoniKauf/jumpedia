from abc import ABC, abstractmethod
import builtins
from dataclasses import dataclass, field
import enum
import datetime as dt
import functools
import json
import pickle
import textwrap
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Iterable, Literal, Never, NotRequired, Optional, Self, TypedDict
from database import queries
import re
from decimal import Decimal
import decimal
from discordtools import messaging as msg
from errors import FeedbackError
import errors
from structures import attributes
import structures
from structures.attributes import AttributeValueType, AttributeValueTypeT
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.base_structure import BaseStructure
from utils import parsetools, text, timetools
from database import typed as typed
from database.typed import Tables as TBL
from utils.locked import equality_locked

if TYPE_CHECKING:
    from structures.list.list import List

_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')

@dataclass(frozen=True, kw_only=True)
class BaseAttribute[T: AttributeValueTypeT](BaseStructure):
    __structure_name__ = "base attribute"

    # --- CONSTANTS ---
    TYPE_ID: ClassVar[int]

    list: 'List'
    id: int 
    name: str
    value_type: AttributeValueType
    index: int
    min_slots: int
    max_slots: int
    unique_slots: bool

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.__class__.TYPE_ID, self.id) + self.list.identity
    
    @property
    def required(self) -> bool:
        return self.min_slots > 0

    # --- Methods ---

    def __post_init__(self) -> None:
        if self.__class__ == BaseAttribute:
            raise NotImplementedError()

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    def get_syns(self) -> set[str]:
        return {self.name} | self.get_aliases()
    
    def has_collection(self) -> bool:
        return bool(self.get_collection().nodes)
    
    @abstractmethod
    def get_aliases(self) -> set[str]:
        pass

    @abstractmethod
    def get_collection(self) -> Collection[T, Any]:
        pass
    
    @classmethod
    def validate_number_valid(cls, number: int | float | Decimal) -> None:
        MIN, MAX = attributes.NUMBER_MIN, attributes.NUMBER_MAX

        if not (MIN <= number <= MAX):
            raise FeedbackError(
                "Number Out Of Valid Range",
                f"The number {msg.shorten_and_code(str(number))} is too small or big!",
                additional=f"It must be a value between {msg.code(str(MIN))} and {msg.code(str(MAX))}."
            )

    _VALUE_TYPE_TO_ADDITIONAL: dict[AttributeValueType, str] = {
        AttributeValueTypeT
    }

    @staticmethod
    def _raise_invalid_value_for_value_type(s: str, value_type: AttributeValueType) -> Never:
        if value_type.quote_required:
            additional_modal_verb = "must also be"
        else:
            additional_modal_verb = "can optionally also be"

        raise FeedbackError(
            "Invalid Value For Required Type",
            f"The value {msg.shorten_and_code(s)} is not valid for attribute's value type {msg.code(value_type.name)}!",
            additional=f"{additional_start}\nThey {additional_modal_verb} wrapped in \"quotation marks\"."
        )
    
    @classmethod
    def from_str_singular(cls, s: str, value_type: AttributeValueType) -> T:
        value_type_type = value_type.type
        s_before, s = s, text.sanitize(s)
        
        if issubclass(value_type_type, bool):
            s = s.lower()

            if s == "false":
                return False  # type: ignore
            if s == "true":
                return True  # type: ignore
            
            cls._raise_invalid_value_for_value_type(s, value_type)

        elif issubclass(value_type_type, int):
            try:
                result = int(s)
            except Exception:
                cls._raise_invalid_value_for_value_type(
                    s, 
                    value_type, 
                    f"These are some examples of valid values:\n" + 
                    '\n'.join(f"- {msg.code_many(("0", "3", "238283283", "-13"))}")
                )
            
            cls.validate_number_valid(result)

            return result  # type: ignore
    
        elif issubclass(value_type_type, Decimal):
            try:
                result = Decimal(s)
                result = result.quantize(Decimal(f"1E-{attributes.DECIMAL_DEC_PART_MAX_LEN}"))
            except Exception:
                cls._raise_invalid_value_for_value_type(
                    s,
                    value_type,
                    f"These are some examples of valid values:\n" + 
                    '\n'.join(f"- {msg.code_many(("0.01", "3", "3.1415926", "-30.7", "148234290329.2382"))}")
                )
            
            cls.validate_number_valid(result)

            return result  # type: ignore
            
        elif issubclass(value_type_type, (dt.time, dt.date, dt.datetime)):
            # If a date is in the type
            if issubclass(value_type_type, (dt.date, dt.datetime)):
                s = re.sub(_DATE_ALTERNATIVE_DELIMITERS_PATTERN, "-", s)
            
            try:
                result = value_type_type.fromisoformat(s)
            except Exception:
                cls._raise_invalid_value_for_value_type(
                    s,
                    value_type,
                    "Todo"
                )
                
            if isinstance(result, (dt.time, dt.datetime)):
                if result.tzinfo is None:
                    result = result.replace(tzinfo=dt.timezone.utc)
                
                if isinstance(result, dt.time):
                    datetime = dt.datetime.combine(dt.date.today(), result, result.tzinfo)
                    return datetime.astimezone(dt.timezone.utc).time()  # type: ignore
                
                return result.astimezone(dt.timezone.utc)  # type: ignore

        if issubclass(value_type_type, dt.timedelta):
            try:
                return timetools.parse_timedelta(s)  # type: ignore
            except ValueError:
                cls._raise_invalid_value_for_value_type(
                    s,
                    value_type,
                    "Todo"
                )

        if issubclass(value_type_type, str):
            MIN, MAX = attributes.STR_MIN_LEN, attributes.STR_MAX_LEN

            if not (MIN <= len(s) <= MAX):
                cls._raise_invalid_value_for_value_type(
                    s,
                    value_type,
                    "Todo"
                )
            
            return s  # type: ignore

        raise errors.ImpossibleError("Invalid AttributeValueType", value_type.type)
    

    def from_loaded(self, loaded: str | builtins.list[Any], custom_value_type: AttributeValueType | None = None) -> builtins.list[T]:
        value_type = custom_value_type or self.value_type

        if isinstance(loaded, list):
            values = loaded
        else:
            values = [loaded]

        converted: list[T] = []

        for elem in values:
            if isinstance(elem, str):
                converted.append(self.from_str_singular(elem, value_type))

            elif isinstance(elem, self.value_type.type) and issubclass(self.value_type.type, (bool, int)):
                converted.append(self.from_str_singular(str(elem), value_type))

            else:
                raise FeedbackError(
                    "Invalid Value Format",
                    "The value must be valid JSON format of either a single value or a list of values."
                )
        
        if not (self.min_slots <= (count := len(converted)) <= self.max_slots):
            raise feedback.TemporaryFeedbackError("Count of values not between limits", self.min_slots, count, self.max_slots)
        
        
        values = self._collection_conversion_if_needed(converted)

        if self.unique_slots:
            if len(values) != len(frozenset(values)):
                raise feedback.TemporaryFeedbackError("Values must be unique for this attribute")
            
        return values

    def from_str(self, s: str, custom_value_type: AttributeValueType | None = None) -> builtins.list[T]:
        if not (s := s.strip()):
            return []
        
        try:
            loaded: str | list[Any] = parsetools.json_loads_safe(s, 1)
        except RecursionError as e:
            raise Exception  # TODO

        return self.from_loaded(loaded, custom_value_type)
        

    def to_str(self, obj: T) -> str:
        if isinstance(obj, (bool, int, Decimal, str)):
            return str(obj)
        
        if isinstance(obj, (dt.time, dt.date, dt.datetime)):
            return obj.isoformat()
        
        if isinstance(obj, (dt.timedelta)):
            return timetools.unparse_timedelta(obj)
        
        raise TypeError("Invalid")

    def _collection_conversion_if_needed(self, elems: Iterable[T]) -> builtins.list[T]:
        if not self.has_collection():
            return list(elems)
        
        result: list[T] = []

        for elem in elems:
            node = self.get_collection().lookup_node(elem, None)
            
            if node is None:
                raise feedback.TemporaryFeedbackError("Not part of collection", elem)

            result.append(node.value)

        return result

    @classmethod
    def _sort_key_singular(cls, value: T, sign: Literal[+1, -1], value_type: AttributeValueType[T]) -> int:
        vt: type[T] = value_type.type

        if issubclass(vt, bool):
            return int(value + 1) * sign  # type: ignore
            
        if issubclass(vt, (int, Decimal)):
            return value * sign  # type: ignore

        if issubclass(vt, dt.time):
            return (
                value.microsecond +           # type: ignore
                value.second *   1_000_000 +  # type: ignore
                value.minute *  60_000_000 +  # type: ignore
                value.hour * 3_600_000_000    # type: ignore
            ) * sign
        
        if issubclass(vt, dt.datetime):
            return value.timestamp() * sign  # type: ignore
         
        if issubclass(vt, dt.date):
            return value.timetuple().tm_yday * sign  # type: ignore
        
        if issubclass(vt, dt.timedelta):
            return value.total_seconds() * sign  # type: ignore
        
        raise TypeError()
        
    def sort_key(self, s: str, sign: Literal[+1, -1]) -> tuple[int, ...] | Any:
        values = self.from_str(s)
        
        if not values:
            return (attributes.SORT_KEY_NONE_NUMBER + 1) * sign
        
        if self.has_collection():
            try:
                return tuple((
                    coll_item.sort_value
                    if (coll_item := self.get_collection().lookup_node(v, None)) is not None
                    else attributes.SORT_KEY_NONE_NUMBER
                ) * sign
                for v in values)
            except KeyError as e:
                raise RuntimeError(
                    f"Sort value for elem '{e.args[0]}' not found, which " +
                    f"should not happen."
                )
        
        return tuple(self._sort_key_singular(value, sign, self.value_type) for value in values)
    
    def is_empty(self, value: str) -> bool:
        return bool(self.from_str(value, None)) 
