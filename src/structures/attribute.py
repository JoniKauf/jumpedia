import builtins
from dataclasses import dataclass, field
import enum
import datetime as dt
import functools
import json
import pickle
from threading import Lock, RLock
from typing import Any, ClassVar, Final, Iterable, Literal, NamedTuple, NotRequired, Optional, Self, Sequence, TypedDict, Union
import typing
from database import queries
from discordtools import feedbackerrors as fbe
import re
from decimal import Decimal
import decimal
from structures.list import List
from utils import parsetools, text, timetools

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

    _attribute_value_types: ClassVar[Final[list[Self]]] = field(init=False, default_factory=list)
    _attribute_value_type_id_lookup: ClassVar[Final[dict[int, Self]]] = field(init=False, default_factory=dict)
    _attribute_value_type_name_lookup: ClassVar[Final[dict[str, Self]]] = field(init=False, default_factory=dict)
    _attribute_value_type_type_lookup: ClassVar[Final[dict[str, Self]]] = field(init=False, default_factory=dict)

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

if AttributeValueTypeT.__value__.__args__ != tuple(vt.value for vt in AttributeValueTypeEnum):  # type: ignore
    raise RuntimeError("Enum does not equal type!!")



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
type CollectionT[T] = CollectionTreeT[T]



# --- Helper Functions --- #

def _parse_user_collection[T: AttributeValueTypeT](
    str_user_collection: str, 
    value_type: AttributeValueType[T],
) -> CollectionT[T]:
    user_value_collection: UserCollectionT = parsetools.json_loads_safe(
        str_user_collection, 
        Attribute.MAX_DEPTH
    )

    if user_value_collection is None:
        return []
    
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
    value_type: AttributeValueType[T]
) -> CollectionTreeT[T]:
    result: CollectionTreeT = []

    for item in user_collection_tree:
        value, display_value, sort_value = _extract_data_from_collection_item(item, value_type)

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

def _extract_data_from_collection_item[T: AttributeValueTypeT](
    item: UserCollectionTreeItemT,
    value_type: AttributeValueType[T]
) -> tuple[T, T, int]:
    try:
        sort_value: int = int(item['sort_value'])
    except KeyError as e:
        raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
    except ValueError as e:
        raise fbe.TemporaryFeedbackError("Not an int")
        
    Attribute.generic_number_valid(sort_value)

    try:
        bad_value = item['value']
    except KeyError as e:
        raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
    
    display_value: T = Attribute._parse_str_singular(bad_value, value_type)
    value: T = Attribute.normalize(display_value)

    return (value, display_value, sort_value)

def _create_collection_lookup[T: AttributeValueTypeT](
    collection_tree: CollectionTreeT[T],
    lookup_ref: dict[T, CollectionTreeItem[T]]
) -> None:
    def recursive(tree: CollectionTreeT[T]) -> None:
        for item in tree:
            if item.value in lookup_ref:
                raise fbe.TemporaryFeedbackError()
            
            lookup_ref[item.value] = item

            recursive(item.nodes)
    
    recursive(collection_tree)



# --- Attribute Table --- #

class AttributeTableT(TypedDict):
    id: int
    list_id: int
    name: str
    display_name: str
    sort_value: int
    alias: list[str]
    value_type: int
    collection: bytes
    min_value_slots: int
    max_value_slots: int
    unique_slots: bool
    user_bound: bool
    unique_in_list: bool
    


#------#   Attribute   #------#	

@dataclass(frozen=True, kw_only=True)
class Attribute[T: AttributeValueTypeT]:
    # --- CONSTANTS ---

    # number
    NUMBER_MAX: ClassVar[Final[int]] = 2 ** 63 - 1
    NUMBER_MIN: ClassVar[Final[int]] = -NUMBER_MAX - 1
    DECIMAL_PRECISION: ClassVar[Final[int]] = decimal.getcontext().prec
    INT_PART_MAX_LEN: ClassVar[Final[int]] = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
    DEC_PART_MAX_LEN: ClassVar[Final[int]] = DECIMAL_PRECISION - INT_PART_MAX_LEN
    DECIMAL_MAX_LEN: ClassVar[Final[int]] = DECIMAL_PRECISION if DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1
    
    # str
    STR_MAX_LEN: ClassVar[Final[int]] = 512

    # Collection
    COLLECTION_MAX_MEMORY: ClassVar[Final[int]] = 1024 * 32
    COLLECTION_MAX_ELEMS: ClassVar[Final[int]] = 1024

    MAX_DEPTH: ClassVar[Final[int]] = 64
    
    # General
    MAX_SYN_LEN: ClassVar[Final[int]] = 32
    MAX_ALIASES: ClassVar[Final[int]] = 31
    MAX_ATTRIBUTES_PER_COMMUNITY: ClassVar[Final[int]] = 50
    MAX_VALUE_SLOTS: ClassVar[Final[int]] = 32

    TABLE_NAME: ClassVar[Final[str]] = "attribute"
    SORT_KEY_LAST_NUMBER: ClassVar[Final[int]] = max(abs(NUMBER_MIN), abs(NUMBER_MAX)) + 1


    list: List
    id: int 
    name: str
    display_name: str
    sort_value: int
    alias: set[str]
    value_type: AttributeValueType
    collection: CollectionT
    collection_lookup: dict[T, CollectionTreeItem] = field(init=False, default_factory=dict)  # Generated, not in DB
    min_value_slots: int
    max_value_slots: int
    unique_slots: bool
    user_bound: bool
    unique_in_list: bool



    # --- Methods ---

    def __post_init__(self) -> None:
        if self.has_collection:
            _create_collection_lookup(self.collection, self.collection_lookup)

    @classmethod
    def create(
        cls,
        list: List,
        bad_name: str,
        bad_aliases: set[str],
        sort_value: int,
        value_type: AttributeValueType[T],
        str_user_collection: str | None,
        min_value_slots: int,
        max_value_slots: int,
        unique_slots: bool,
        user_bound: bool,
        unique_in_list: bool
    ):
        name, display_name = text.create_name_and_display_name(
            bad_name, 
            True, 
            Attribute.MAX_SYN_LEN, 
            (a.name for a in list.get_attributes())
        )

        alias = text.fix_aliases(bad_aliases, Attribute.MAX_SYN_LEN, Attribute.MAX_ALIASES)
        
        Attribute.generic_number_valid(sort_value)
        
        if not (1 <= max_value_slots <= Attribute.MAX_VALUE_SLOTS):
            raise fbe.TemporaryFeedbackError()

        if not (0 <= min_value_slots <= max_value_slots):
            raise fbe.TemporaryFeedbackError()
        
        if user_bound and unique_in_list:
            raise fbe.TemporaryFeedbackError()
        
        if str_user_collection is None or not str_user_collection.strip():
            collection: CollectionT[T] = []
        else:
            collection = _parse_user_collection(str_user_collection, value_type)

        pickled_value_collection: bytes = pickle.dumps(collection)
        h = queries.ArgHelper()

        with queries.connected(list.community) as (conn, cursor):
            cursor.execute(f"""
                INSERT INTO {h|Attribute.TABLE_NAME} (
                    list_id,
                    name,
                    display_name
                    sort_value,
                    alias,
                    value_type,
                    collection,
                    min_value_slots,
                    max_value_slots,
                    unique_slots,
                    user_bound,
                    unique_in_list
                )
                VALUES (
                    {h|list.id},
                    {h|name},
                    {h|display_name},
                    {h|sort_value},
                    {h|alias},
                    {h|value_type.id},
                    {h|pickled_value_collection},
                    {h|min_value_slots},
                    {h|max_value_slots},
                    {h|unique_slots},
                    {h|user_bound},
                    {h|unique_in_list}
                )
            """, h.steal())
            
            obj = Attribute(
                list=list,
                id=cursor.lastrowid,  # type: ignore
                name=name,
                display_name=display_name,
                sort_value=sort_value,
                alias=alias,
                value_type=value_type,
                collection=collection,
                min_value_slots=min_value_slots,
                max_value_slots=max_value_slots,
                unique_slots=unique_slots,
                user_bound=user_bound,
                unique_in_list=unique_in_list
            ) 

        return obj
    
    def __hash__(self) -> int:
        return hash((self.id, hash(self.list)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Attribute) and self.id == value.id and self.list == value.list
    
    @property
    def syns(self) -> set[str]:
        return {self.name} | self.alias
    
    @property
    def required(self) -> bool:
        return self.min_value_slots > 0
    
    @property
    def has_collection(self) -> bool:
        return bool(self.collection)
    
    @classmethod
    def generic_number_valid(cls, number: int | float | Decimal) -> None:
        if not (Attribute.NUMBER_MIN < number < Attribute.NUMBER_MAX):
            raise fbe.OutsideOfValidRange(number, Attribute.NUMBER_MIN, Attribute.NUMBER_MAX)
    
    @functools.lru_cache()
    def normalize(self, unnormalized: T) -> T:
        if isinstance(unnormalized, str):
            normalized: T = text.norm(unnormalized, ' ')  # type: ignore
        else:
            normalized = unnormalized
        
        return normalized
    
    @classmethod
    def _parse_str_singular(cls, s: str, value_type: AttributeValueType[T]) -> T:
        vt = value_type.type

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
            
            cls.generic_number_valid(result)
    
        elif issubclass(vt, Decimal):
            try:
                result = Decimal(s)
                result = result.quantize(Decimal(f"1E-{Attribute.DEC_PART_MAX_LEN}"))
            except Exception:
                raise fbe.NotAProperValue("decimal", s)
            
            cls.generic_number_valid(result)
            
        if issubclass(vt, (dt.time, dt.date, dt.datetime)):
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

        if issubclass(vt, dt.timedelta):
            result = timetools.parse_timedelta(s)

        if issubclass(vt, str):
            if len(s) > Attribute.STR_MAX_LEN:
                raise fbe.TooLongValue("string", s, Attribute.STR_MAX_LEN)
            
            result = text.fix_whitespace(s, " ", True)
        
        return result  # type: ignore
    
    def parse_str(self, s: str, normed: bool | None, value_type: AttributeValueType | None = None) -> builtins.list[T]:
        """normed == None -> Do fastest operation because we don't care"""
        if not (s := s.strip()):
            return []
        
        try:
            v: str | list[str] = parsetools.json_loads_safe(s, 1)
        except fbe.TemporaryFeedbackError:  # TODO if depth too big, custom feedback
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

        if not self.has_collection:
            if normed is True:
                for i, elem in enumerate(converted):
                    converted[i] = self.normalize(elem)
        else:
            for i, elem in enumerate(converted):
                elem = self.normalize(elem)

                if elem not in self.collection_lookup:
                    raise fbe.TemporaryFeedbackError()
                
                if normed is False:
                    converted[i] = self.collection_lookup[elem].display_value

        return converted

    def _sort_key_singular(self, value: T | None, sign: Literal[+1, -1]):
        vt: type[T] = self.value_type.type

        assert value is None or type(value) == vt

        if issubclass(vt, bool):
            if value is None:
                value = 3  # type: ignore

            return int(value + 1) * sign  # type: ignore
            
        if issubclass(vt, int):
            if value is None:
                return Attribute.SORT_KEY_LAST_NUMBER * sign

            return value * sign  # type: ignore
        
        if issubclass(vt, Decimal):
            if value is None:
                return Attribute.SORT_KEY_LAST_NUMBER * sign
            
            return value * sign  # type: ignore
        
        add = 1 if value is None else 0

        if issubclass(vt, dt.time):
            if value is None:
                value = dt.time.max  # type: ignore
                
            return ((
                value.microsecond +           # type: ignore
                value.second *   1_000_000 +  # type: ignore
                value.minute *  60_000_000 +  # type: ignore
                value.hour * 3_600_000_000    # type: ignore
            ) + add) * sign
        
        if issubclass(vt, dt.datetime):
            if value is None:
                value = dt.datetime.max  # type: ignore
            
            return (value.timestamp() + add) * sign  # type: ignore
         
        if issubclass(vt, dt.date):
            if value is None:
                value = dt.date.max  # type: ignore
            
            return (value.timetuple().tm_yday + add) * sign  # type: ignore
        
        if issubclass(vt, dt.timedelta):
            if value is None:
                value = dt.timedelta.max  # type: ignore
            
            return (value.total_seconds() + add) * sign  # type: ignore
        
    def sort_key(self, value: str, sign: Literal[+1, -1]) -> tuple[int, ...] | Any:
        values = self.parse_str(value, True)
        
        if not values:
            return Attribute.SORT_KEY_LAST_NUMBER + 1
        
        if self.has_collection:
            try:
                return tuple(
                    self.collection_lookup[elem].sort_value * sign for elem in values
                )
            except KeyError as e:
                raise RuntimeError(
                    f"Sort value for elem '{e.args[0]}' not found, which " +
                    f"should not happen."
                )
        
        return tuple(self._sort_key_singular(value, sign) for value in values)
    
    def is_empty(self, value: str) -> bool:
        return bool(self.parse_str(value, None)) 

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