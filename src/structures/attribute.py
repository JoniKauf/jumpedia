from dataclasses import dataclass, field
import enum
import datetime as dt
import functools
import json
import pickle
from threading import Lock, RLock
from typing import Any, ClassVar, Iterable, Literal, NamedTuple, NotRequired, Optional, Self, Sequence, TypedDict, Union
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
from utils import metautils, text, timetools, jsonutils

# --- Constants --- #

_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')



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
    root: Optional['CollectionTreeItem[T]'] = None
type CollectionTreeT[T] = list[CollectionTreeItem[T]]

type UserCollectionT = None | UserCollectionTreeT
type CollectionT[T] = None | CollectionTreeT[T]



# --- Helper Functions --- #

def _parse_user_collection[T: AttributeValueTypeT](
    user_value_collection: UserCollectionT, 
    value_type: AttributeValueType[T],
) -> CollectionT:
    if user_value_collection is None:
        return None
    
    if not isinstance(user_value_collection, list):
        raise fbe.TemporaryFeedbackError("Not a tree")
    
    tree = _parse_user_collection_tree(user_value_collection, value_type)

    _add_roots(tree, None)

    return tree

def _add_roots[T: AttributeValueTypeT](
    tree: CollectionTreeT[T],
    root: CollectionTreeItem[T] | None
) -> None:
    for item in tree:
        object.__setattr__(item, 'root', root)

        _add_roots(item.nodes, item)

def _parse_user_collection_tree[T: AttributeValueTypeT](
    user_collection_tree: UserCollectionTreeT, 
    value_type: AttributeValueType[T],
) -> CollectionTreeT[T]:
    result: CollectionTreeT = []

    for item in user_collection_tree:
        value, display_value, sort_value = _extract_generic_data_from_collection_item(item, value_type)

        sub_trees = item.get('children', [])

        if not isinstance(sub_trees, list):
            raise fbe.TemporaryFeedbackError("Not a sub tree")
        
        item = CollectionTreeItem(
            value,
            display_value,
            sort_value,
            _parse_user_collection_tree([sub_tree for sub_tree in sub_trees], value_type)
        )

        result.append(item)

    return result

def _extract_generic_data_from_collection_item[T: AttributeValueTypeT](
    item: UserCollectionTreeItemT,
    value_type: AttributeValueType[T]
) -> tuple[T, T, int]:
    try:
        sort_value: int = int(item['sort_value'])
    except KeyError as e:
        raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
    except ValueError as e:
        raise fbe.TemporaryFeedbackError("Not an int")
        
    Attribute._check_generic_number_valid(sort_value)

    try:
        bad_value = item['value']
    except KeyError as e:
        raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
    
    display_value: T = Attribute._parse_str_singular(bad_value, value_type)
    value: T = Attribute.normalize(display_value)

    return (value, display_value, sort_value)

def _create_collection_lookup[T: AttributeValueTypeT](
    collection_tree: CollectionTreeT[T],
    yet_empty_collection: dict[T, CollectionTreeItem[T]]
) -> dict[T, CollectionTreeItem[T]]:
    for item in collection_tree:
        if item.value in yet_empty_collection:
            raise fbe.TemporaryFeedbackError()
        
        yet_empty_collection[item.value] = item

        _create_collection_lookup(item.nodes, yet_empty_collection)
    
    return yet_empty_collection

# --- Attribute Table --- #

class AttributeTableT(TypedDict):
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

    # --- CONSTANTS ---

    # number
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


    list_: List
    id: int 
    name: str
    display_name: str
    sort_value: int
    alias: set[str]
    value_type: AttributeValueType
    value_collection: CollectionT
    value_collection_lookup: dict[T, CollectionTreeItem] = field(init=False, default_factory=dict)  # Generated, not in DB
    min_value_slots: int
    max_value_slots: int
    unique_slots: bool
    user_bound: bool
    unique_in_list: bool

    # --- Methods ---

    def __post_init__(self) -> None:
        self.value_collection_lookup = _
    @classmethod
    def create(
        cls,
        list: List,
        bad_name: str,
        bad_aliases: set[str],
        sort_value: int,
        value_type: AttributeValueType[T],
        user_value_collection: str | None,
        min_value_slots: int,
        max_value_slots: int,
        unique_slots: bool,
        user_bound: bool,
        unique_in_list: bool,
    ):
        with list.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True, 
                Attribute.MAX_SYN_LEN, 
                (a.name for a in list.get_attributes())
            )

            alias = text.fix_aliases(bad_aliases, Attribute.MAX_SYN_LEN, Attribute.MAX_ALIASES)
            
            Attribute._check_generic_number_valid(sort_value)
            
            if not (1 <= max_value_slots <= Attribute.MAX_VALUE_SLOTS):
                raise fbe.TemporaryFeedbackError()

            if not (0 <= min_value_slots <= max_value_slots):
                raise fbe.TemporaryFeedbackError()
            
            if user_bound and unique_in_list:
                raise fbe.TemporaryFeedbackError()
            
            if user_value_collection is not None:
                value_collection: CollectionT = _parse_user_collection(
                    jsonutils.json_loads_safe(user_value_collection, Attribute.MAX_DEPTH), 
                    value_type,
                    value_collection_lookup := {}
                )
            else:
                value_collection = None

            pickled_value_collection: bytes = pickle.dumps(value_collection)

            with queries.connected(list.community) as (conn, cursor):
                p = queries.ParamHelper()

                cursor.execute(f"""
                    INSERT INTO {p(Attribute.TABLE_NAME)} (
                        list_id,
                        name,
                        display_name
                        sort_value,
                        alias,
                        value_type,
                        value_collection,
                        min_value_slots,
                        max_value_slots,
                        user_bound,
                        unique_in_list
                    )
                    VALUES (
                        {p(list.id)},
                        {p(name)},
                        {p(display_name)},
                        {p(sort_value)},
                        {p(alias)},
                        {p(value_type.id)},
                        {p(pickled_value_collection)},
                        {p(min_value_slots)},
                        {p(max_value_slots)},
                        {p(user_bound)},
                        {p(unique_in_list)}
                    )
                """, p.params())
                
                obj = Attribute(
                    list,
                    cursor.lastrowid,  # type: ignore
                    name,
                    display_name,
                    sort_value,
                    alias,
                    value_type,
                    value_collection,
                    value_collection_lookup,
                    min_value_slots,
                    max_value_slots,
                    unique_slots,
                    user_bound,
                    unique_in_list
                ) 

            return obj
    
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
    
    def parse_str(self, s: str, value_type: AttributeValueType | None = None) -> list[T]:
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

        if self.collection is not None:
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