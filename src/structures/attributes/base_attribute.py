from abc import ABC, abstractmethod
import builtins
from dataclasses import dataclass, field
import enum
import datetime as dt
import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Iterable, Literal, Never, NotRequired, Optional, Self, TypedDict, Union, assert_never
from database import dbutils, queries
import re
from decimal import Decimal
import decimal
from discordtools import messaging as msg
from errors.feedback import FeedbackError, feedbacks
import errors
from structures import attributes
from structures.attributes import AnyAttributeT, AttributeDataCache, AttributeValueParseTypesT, RawCollectionNode, RawCollectionNodesT, Uniqueness
from structures.attributes import collection as coll
from structures.attributes import slot_type
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.attributes.slot_type import SlotType, SlotTypeT
from structures.base_structure import BaseStructure
from utils import numbers, parsetools, text
from database import typed as typed
from database.typed import Tables as Tables

if TYPE_CHECKING:
    from structures.list import List

        

@dataclass(frozen=True, kw_only=True)
class BaseAttribute[T: SlotTypeT](BaseStructure):
    __structure_name__ = "base attribute"

    # --- CONSTANTS ---
    TYPE_ID: ClassVar[int]

    list: 'List'
    id: int 
    name: str
    slot_type: SlotType[T]
    position: int
    min_slots: int
    max_slots: int
    uniqueness: Uniqueness

    value_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=coll.MAX_DEPTH,
        strict_type=attributes.ATTRIBUTE_VALUE_PARSE_TYPES
    )
    
    _cache: AttributeDataCache[T] = field(init=False, default_factory=AttributeDataCache)

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
    
    def get_aliases(self) -> frozenset[str]:
        assert isinstance(self, attributes.ANY_ATTRIBUTE)

        if self._cache.aliases is not None:
            return self._cache.aliases
        
        TblAlias = dbutils.get_attribute_alias_table(type(self))

        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TblAlias.alias}
                FROM {TblAlias}
                WHERE {TblAlias._attribute_id} = {h|self.id}
            """)

            rows: queries.ManyRowsT = cursor.fetchall()
        
        self._cache.aliases = frozenset(row[TblAlias.alias] for row in rows)

        return self._cache.aliases
    
    @abstractmethod
    def get_collection(self) -> Collection[T]:
        pass

    def value_from_loaded(self, loaded: AttributeValueParseTypesT) -> builtins.list[T]:
        if not isinstance(loaded, list):
            loaded = [loaded]

        if not (self.min_slots <= (count := len(loaded)) <= self.max_slots):
            raise feedbacks.temp("Count of values not between limits", min=self.min_slots, count=count, max=self.max_slots)
        
        result_values: list[T] = []
        
        for slot in loaded:
            if not isinstance(slot, self.slot_type.type):
                raise feedbacks.temp(f"not list, str or value type '{loaded}'")
            
            if not self.slot_type.literal_to_str_possible:
                raise feedbacks.temp(f"value type '{self.slot_type}' is not valid")
            
            parsed_value = self.slot_type.slot_from_str(str(slot))

            result_values.append(parsed_value)
        
        values = self._convert_to_collection(result_values)

        normed_to_val: dict[T, T] = {}
        unique_slots: bool = self.uniqueness >= Uniqueness.PER_VALUE

        for v in values:
            normed_v = self.slot_type.norm(v)
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

    def _convert_to_collection(self, value: builtins.list[T]) -> builtins.list[T]:
        collection = self.get_collection()

        if not collection.is_empty:
            return value
        
        result: list[T] = []
        
        for slot in value:
            node = collection.lookup_node(slot, None)
            
            if node is None:
                raise feedbacks.temp("Not part of the collection", slot)

            result.append(node.value)

        return result

    @classmethod
    def _sort_key_singular(cls, value: T, sign: Literal[+1, -1], slot_type: SlotType[T]) -> int:
        st: type[T] = slot_type.type

        if issubclass(st, bool):
            return int(value + 1) * sign  # type: ignore
            
        if issubclass(st, (int, Decimal)):
            return value * sign  # type: ignore

        if issubclass(st, dt.time):
            return (
                value.microsecond +           # type: ignore
                value.second *   1_000_000 +  # type: ignore
                value.minute *  60_000_000 +  # type: ignore
                value.hour * 3_600_000_000    # type: ignore
            ) * sign
        
        if issubclass(st, dt.datetime):
            return value.timestamp() * sign  # type: ignore
         
        if issubclass(st, dt.date):
            return value.timetuple().tm_yday * sign  # type: ignore
        
        if issubclass(st, dt.timedelta):
            return value.total_seconds() * sign  # type: ignore
        
        raise TypeError()
        
    def sort_key(self, v: builtins.list[T], sign: Literal[+1, -1]) -> tuple[int, ...]:        
        if not v:
            return (attributes.SORT_KEY_NONE_NUMBER + 1) * sign,
        
        collection = self.get_collection()

        if collection.is_empty:
            return tuple(
                self._sort_key_singular(value, sign, self.slot_type) 
                for value in v
            )

        return tuple((
                coll_item.sort_value
                if (coll_item := collection.lookup_node(slot, None)) is not None
                else attributes.SORT_KEY_NONE_NUMBER
            ) * sign
            for slot in v
        )

    def is_valid_value(self, value: builtins.list) -> bool:
        if not isinstance(value, list):
            return False
        
        return all(self.slot_type.is_valid_slot(slot) for slot in value)