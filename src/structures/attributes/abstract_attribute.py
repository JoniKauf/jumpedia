from abc import ABC, abstractmethod
import builtins
from dataclasses import dataclass, field
import enum
import datetime as dt
import functools
import json
import pickle
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Iterable, Literal, Never, NotRequired, Optional, Self, TypedDict
from database import queries
from discord_structures import errors, feedbackerrors as fbe
import re
from decimal import Decimal
import decimal
from structures import attributes
from structures.attributes import AttributeValueType, AttributeValueTypeT
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from utils import parsetools, text, timetools
from database import typed as typed
from database.typed import Tables as TBL
from utils.locked import equality_locked

if TYPE_CHECKING:
    from structures.list.list import List

_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')


@dataclass(kw_only=True)
class AbstractAttribute[T: AttributeValueTypeT](ABC):

    # --- CONSTANTS ---
    ATTRIBUTE_TYPE_NAME: ClassVar[str]
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
        if self.__class__ == AbstractAttribute:
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
    def any_number_valid(cls, number: int | float | Decimal) -> None:
        if not (attributes.NUMBER_MIN <= number <= attributes.NUMBER_MAX):
            raise fbe.OutsideOfValidRange(number, attributes.NUMBER_MIN, attributes.NUMBER_MAX)
    
    @classmethod
    def from_str_singular(cls, s: str, value_type: AttributeValueType[T]) -> T:
        vt = value_type.type
        s = text.sanitize(s)

        if issubclass(vt, bool):
            s = s.lower()

            if s in "false":
                result = False
            elif s == "true":
                result = True
            else:
                raise fbe.NotAProperValue("boolean", s)

        elif issubclass(vt, int):
            try:
                result = int(s)
            except Exception:
                raise fbe.NotAProperValue("integer", s)
            
            cls.any_number_valid(result)
    
        elif issubclass(vt, Decimal):
            try:
                result = Decimal(s)
                result = result.quantize(Decimal(f"1E-{attributes.DECIMAL_DEC_PART_MAX_LEN}"))
            except Exception:
                raise fbe.NotAProperValue("decimal", s)
            
            cls.any_number_valid(result)
            
        elif issubclass(vt, (dt.time, dt.date, dt.datetime)):
            # If a date is in the type
            if issubclass(vt, (dt.date, dt.datetime)):
                s = re.sub(_DATE_ALTERNATIVE_DELIMITERS_PATTERN, "-", s)
            
            try:
                result = vt.fromisoformat(s)
            except Exception:
                raise fbe.TemporaryFeedbackError("Invalid datetime repr")
            
            if isinstance(result, (dt.time, dt.datetime)):
                if result.tzinfo is None:
                    result = result.replace(tzinfo=dt.timezone.utc)
                
                if isinstance(result, dt.time):
                    datetime = dt.datetime.combine(dt.date.today(), result, result.tzinfo)
                    result = datetime.astimezone(dt.timezone.utc).time()
                else:
                    result = result.astimezone(dt.timezone.utc)

        elif issubclass(vt, dt.timedelta):
            result = timetools.parse_timedelta(s)

        elif issubclass(vt, str):
            if len(s) > attributes.STR_MAX_LEN:
                raise fbe.TooLongValue("string", s, attributes.STR_MAX_LEN)
            
            result = s
        
        else:
            raise TypeError()
        
        return result  # type: ignore
    

    def from_loaded(self, loaded: str | builtins.list[Any], custom_value_type: AttributeValueType | None = None) -> builtins.list[T]:
        value_type = custom_value_type or self.value_type

        converted: list[T] = []

        if isinstance(loaded, list):
            values = loaded
        else:
            values = [loaded]

        for elem in values:
            if isinstance(elem, str):
                if not elem.strip():
                    continue
                
                converted.append(self.from_str_singular(elem, value_type))
            elif isinstance(elem, self.value_type.type) and issubclass(self.value_type.type, (bool, int)):
                converted.append(elem)
            else:
                raise fbe.TemporaryFeedbackError
        
        if not (self.min_slots <= (count := len(converted)) <= self.max_slots):
            raise fbe.TemporaryFeedbackError("Count of values not between limits", self.min_slots, count, self.max_slots)
        
        values = self._collection_conversion_if_needed(converted)

        if self.unique_slots:
            if len(values) != len(frozenset(values)):
                raise fbe.TemporaryFeedbackError("Values must be unique for this attribute")
            
        return values

    def from_str(self, s: str, custom_value_type: AttributeValueType | None = None) -> builtins.list[T]:
        if not (s := s.strip()):
            return []
        
        try:
            loaded: str | list[Any] = parsetools.json_loads_safe(s, 1)
        except fbe.TemporaryFeedbackError:  # TODO if depth too big, custom feedback
            raise fbe.TemporaryFeedbackError 

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
                raise fbe.TemporaryFeedbackError("Not part of collection", elem)

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
