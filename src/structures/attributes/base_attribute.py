from abc import ABC, abstractmethod
import builtins
from dataclasses import dataclass, field
import enum
import datetime as dt
import json
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Iterable, Literal, Never, NotRequired, Optional, Self, TypedDict, Union
from database import queries
import re
from decimal import Decimal
import decimal
from discordtools import messaging as msg
from errors.feedback import FeedbackError, feedbacks
import errors
from structures import attributes
from structures.attributes import AttributeValueType, AttributeValueTypeT, Uniqueness
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.base_structure import BaseStructure
from utils import parsetools, text
from database import typed as typed
from database.typed import Tables as TBL

if TYPE_CHECKING:
    from structures.list import List

_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')

@dataclass(frozen=True, kw_only=True)
class BaseAttribute[T: AttributeValueTypeT](BaseStructure):
    __structure_name__ = "base attribute"

    # --- CONSTANTS ---
    TYPE_ID: ClassVar[int]

    list: 'List'
    id: int 
    name: str
    value_type: AttributeValueType[T]
    index: int
    min_slots: int
    max_slots: int
    uniqueness: Uniqueness

    value_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=attributes.COLLECTION_MAX_DEPTH,
        strict_type=attributes.ATTRIBUTE_VALUE_PARSE_TYPES
    )
    

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
    def get_collection(self) -> Collection[T]:
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
        
    @staticmethod
    def _feedback_invalid_value_for_value_type(s: str, value_type: AttributeValueType, additional_start: str) -> FeedbackError:
        if value_type.literal_to_str_possible:
            additional_modal_verb = "must also be"
        else:
            additional_modal_verb = "can optionally also be"

        raise FeedbackError(
            "Invalid Value For Required Type",
            f"The value {msg.shorten_and_code(s)} is not valid for attribute's value type {msg.code(value_type.name)}!",
            additional=f"{additional_start}\nThey {additional_modal_verb} wrapped in \"quotation marks\"."
        )
    
    @classmethod
    def slot_from_str(cls, s: str, value_type: AttributeValueType) -> T:
        value_type_type = value_type.type
        old_s, s = s, text.sanitize(s)

        if not s:
            raise feedbacks.temp(f"empty or only whitespace values like {msg.code(old_s)} are not allowed")
        
        if issubclass(value_type_type, bool):
            s = s.lower()

            if s == "false":
                return False  # type: ignore
            if s == "true":
                return True  # type: ignore
            
            raise cls._feedback_invalid_value_for_value_type(s, value_type, f"The only valid values are {msg.code('true')} or {msg.code('false')}.")

        elif issubclass(value_type_type, int):
            try:
                result = int(s)
            except Exception:
                raise cls._feedback_invalid_value_for_value_type(
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
                raise cls._feedback_invalid_value_for_value_type(
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
                raise cls._feedback_invalid_value_for_value_type(
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
                return parsetools.parse_timedelta(s)  # type: ignore
            except ValueError:
                raise cls._feedback_invalid_value_for_value_type(
                    s,
                    value_type,
                    "Todo"
                )

        if issubclass(value_type_type, str):
            MIN, MAX = attributes.STR_MIN_LEN, attributes.STR_MAX_LEN

            if not (MIN <= len(s) <= MAX):
                raise cls._feedback_invalid_value_for_value_type(
                    s,
                    value_type,
                    "Todo"
                )
            
            return s  # type: ignore

        raise errors.ImpossibleError("Invalid AttributeValueType", value_type.type)
    

    def value_from_loaded(self, loaded: attributes.AttributeValueParseTypesT) -> builtins.list[T]:
        if not isinstance(loaded, list):
            loaded = [loaded]

        if not (self.min_slots <= (count := len(loaded)) <= self.max_slots):
            raise feedbacks.temp("Count of values not between limits", min=self.min_slots, count=count, max=self.max_slots)
        
        result_values: list[T] = []
        
        for slot in loaded:
            if not isinstance(slot, self.value_type.type):
                raise feedbacks.temp(f"not list, str or value type '{loaded}'")
            
            if not self.value_type.literal_to_str_possible:
                raise feedbacks.temp(f"value type '{self.value_type}' is not valid")
            
            parsed_value = self.__class__.slot_from_str(str(slot), self.value_type)

            result_values.append(parsed_value)
        
        values = self._collection_conversion_if_needed(result_values)

        normed_to_val: dict[T, T] = {}
        unique_slots: bool = self.uniqueness >= Uniqueness.PER_VALUE

        for v in values:
            normed_v = self.value_type.norm(v)
            other_v = normed_to_val.get(normed_v, None)

            if other_v is None:
                normed_to_val[normed_v] = v
                continue
            
            if unique_slots:
                raise feedbacks.temp(f"For the attribute {self.name} the slots must be unique. The value {v} appeared multiple times.")

            if other_v != v:
                raise feedbacks.temp(f"All values that are equal case insensitively must be exactly equal. {other_v} != {v}")

        return values
    
    def value_from_str(self, s: str) -> Any:
        return self.value_from_str(self.__class__.general_from_str(
            s, 
            self.__class__.value_parser
        ))

    @classmethod
    def general_from_str[T_: attributes.AttributeValueParseTypesT](cls, s: str, parser: parsetools.SafeJsonParser[T_]) -> T_:
        try:
            return parser.loads(s)
        except json.JSONDecodeError as e:
            raise feedbacks.temp(f"Not valid json at ...{e.msg[e.pos:e.pos + 10]}...")
        except RecursionError as e:
            raise feedbacks.temp(f"Max depth for json exceeded")
        except TypeError as e:
            raise feedbacks.temp(f"object {msg.code(e.args[0])} is not of type {msg.code(e.args[1])}")
        except Exception:
            raise feedbacks.temp("Unknown json parse exception")
        

    def to_str(self, obj: T) -> str:
        if isinstance(obj, (bool, int, Decimal, str)):
            return str(obj)
        
        if isinstance(obj, (dt.time, dt.date, dt.datetime)):
            return obj.isoformat()
        
        if isinstance(obj, (dt.timedelta)):
            return parsetools.unparse_timedelta(obj)
        
        raise TypeError("Invalid")

    def _collection_conversion_if_needed(self, elems: builtins.list[T]) -> builtins.list[T]:
        if not self.has_collection():
            return elems
        
        result: list[T] = []

        for elem in elems:
            node = self.get_collection().lookup_node(elem, None)
            
            if node is None:
                raise feedbacks.temp("Not part of the collection", elem)

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
        values = self.value_from_str(s)
        
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