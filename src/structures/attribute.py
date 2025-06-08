from abc import ABC
import builtins
from dataclasses import dataclass, field
import enum
import datetime as dt
import functools
import json
import pickle
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Iterable, Literal, Never, NotRequired, Optional, Self, TypedDict
from database import queries
from discordtools import errors, feedbackerrors as fbe
import re
from decimal import Decimal
import decimal
from utils import parsetools, text, timetools
from database import strong as S
from database.strong import Tables as TBL
from utils.locked import equality_locked

if TYPE_CHECKING:
    from structures.list import List

# --- Constants --- #

_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')

type AnyAttributeT[T: AttributeValueTypeT] = StaticAttribute[T] | TaskAttribute[T] | UserAttribute[T]


# --- Attribute Value Type --- #

type AttributeValueTypeT = (
    bool | int | Decimal | 
    dt.time | dt.date | dt.datetime | dt.timedelta | 
    str
)

type_ = type

@dataclass
class AttributeValueType[T: AttributeValueTypeT]:
    id: int
    name: str
    type: type[T]

    _attribute_value_types: ClassVar[list[Self]] = []
    _attribute_value_type_id_lookup: ClassVar[dict[int, Self]] = {}
    _attribute_value_type_name_lookup: ClassVar[dict[str, Self]] = {}
    _attribute_value_type_type_lookup: ClassVar[dict[str, Self]] = {}

    def __hash__(self):
        return hash((self.id, self.name, self.type.__qualname__))
    
    def __post_init__(self):
        for elem in AttributeValueType._attribute_value_types:
            if self.name == elem.name or self.id == elem.id or self.type == elem.type:
                raise errors.ProgrammingError()
            
        AttributeValueType._attribute_value_types.append(self)
        AttributeValueType._attribute_value_type_id_lookup[self.id] = self
        AttributeValueType._attribute_value_type_name_lookup[self.name] = self
        AttributeValueType._attribute_value_type_type_lookup[self.type.__qualname__] = self

    @classmethod
    def get_by_id(cls, id: int) -> Self:
        try:
            return cls._attribute_value_type_id_lookup[id]
        except KeyError as e:
            raise LookupError(*e.args)
        
    @classmethod
    def get_by_name(cls, name: str) -> Self:
        try:
            return cls._attribute_value_type_name_lookup[name]
        except KeyError as e:
            raise LookupError(*e.args)
        
    @classmethod
    def get_by_type(cls, type: type_[T]) -> 'AttributeValueType[T]':
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
    'AttributeValueTypeEnum', [(avt.name, avt) for avt in AttributeValueType._attribute_value_types] + []
)

if AttributeValueTypeT.__value__.__args__ != tuple(vt.value.type for vt in AttributeValueTypeEnum):  # type: ignore
    raise RuntimeError("Enum does not equal type!!")


@dataclass(unsafe_hash=True)
class CollectionTreeItem[T]:
    value: T
    aliases: set[T]
    sort_value: int
    nodes: 'CollectionTreeT[T]'
    root: 'CollectionTreeItem[T] | None' = None
type CollectionTreeT[T] = list[CollectionTreeItem[T]]


def _generate_collection[T: AttributeValueTypeT](
    rows: S.ManyTableRowT, 
    table: type[TBL.TaskAttributeCollectionNode | TBL.UserAttributeCollectionNode]
) -> tuple[CollectionTreeT[T], dict[T, CollectionTreeItem[T]]]:
    if not rows:
        return [], {}
    
    lookup_by_id: dict[int, CollectionTreeItem[T]] = {}
    lookup_by_syn: dict[T, CollectionTreeItem[T]] = {}

    result: CollectionTreeT[T] = []

    # Create objects without nodes / root references
    for row in rows:
        id = row[table.id]
        
        item = CollectionTreeItem(
            value=pickle.loads(row[table.value]),
            aliases=set(json.loads(row[table._aliases])),
            sort_value=row[table.sort_value],
            nodes=[],
            root=None
        )

        lookup_by_id[id] = item
        
        # Create lookup via syn
        for syn in (item.value, *item.aliases):
            syn = _normalize_collection_value(syn)

            if syn in lookup_by_syn:
                raise errors.ProgrammingError(
                    "Syns from collection, retrieved from database, result in collision?\n" +
                    f"For table {table}, rows {rows}"
                )
            
            lookup_by_syn[syn] = item

    # Create references of nodes / root
    for row in rows:
        id = row[table.id]
        root_id = row[table.root_id]

        if root_id is None:
            result.append(lookup_by_id[id])
            continue

        node = lookup_by_id[id]
        root = lookup_by_id[root_id]

        root.nodes.append(node)
        node.root = root

    return result, lookup_by_syn


def _normalize_collection_value[T: AttributeValueTypeT](value: T) -> T:
    if isinstance(value, str):
        return text.norm(value)
    
    return value

#------#   Attribute   #------#	

@dataclass(kw_only=True)
class AbstractAttribute[T: AttributeValueTypeT]:
    # --- CONSTANTS ---

    # number
    NUMBER_MAX: ClassVar[int] = 2 ** 63 - 1
    NUMBER_MIN: ClassVar[int] = -NUMBER_MAX - 1
    DECIMAL_PRECISION: ClassVar[int] = decimal.getcontext().prec
    DECIMAL_INT_PART_MAX_LEN: ClassVar[int] = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
    DECIMAL_DEC_PART_MAX_LEN: ClassVar[int] = DECIMAL_PRECISION - DECIMAL_INT_PART_MAX_LEN
    DECIMAL_MAX_STR_LEN: ClassVar[int] = DECIMAL_PRECISION if DECIMAL_DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1
    
    # str
    STR_MAX_LEN: ClassVar[int] = 512

    # Collection
    COLLECTION_MAX_MEMORY: ClassVar[int] = 1024 * 32
    COLLECTION_MAX_ELEMS: ClassVar[int] = 1024
    COLLECTION_MAX_DEPTH: ClassVar[int] = 16
    
    # General
    MAX_SYN_LEN: ClassVar[int] = 32
    MAX_ALIAS_COUNT: ClassVar[int] = 32
    MAX_COLLECTION_ALIASES: ClassVar[int] = 7
    MAX_SLOTS: ClassVar[int] = 32
    SORT_KEY_NONE_NUMBER: ClassVar[int] = max(abs(NUMBER_MIN), abs(NUMBER_MAX)) + 1

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
        return bool(self.get_collection())
    
    def get_aliases(self) -> set[str]:
        raise NotImplementedError()

    def get_collection(self) -> CollectionTreeT[T]:
        raise NotImplementedError()
    
    def get_collection_item_by_value(self, value: T) -> CollectionTreeItem[T] | None:
        raise NotImplementedError()
    
    @classmethod
    def any_number_valid(cls, number: int | float | Decimal) -> None:
        if not (AbstractAttribute.NUMBER_MIN < number < AbstractAttribute.NUMBER_MAX):
            raise fbe.OutsideOfValidRange(number, AbstractAttribute.NUMBER_MIN, AbstractAttribute.NUMBER_MAX)
    
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
                result = result.quantize(Decimal(f"1E-{AbstractAttribute.DECIMAL_DEC_PART_MAX_LEN}"))
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
            if len(s) > AbstractAttribute.STR_MAX_LEN:
                raise fbe.TooLongValue("string", s, AbstractAttribute.STR_MAX_LEN)
            
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

    def _collection_conversion_if_needed(self, elems: Iterable[T]) -> builtins.list[T]:
        if not self.has_collection():
            return list(elems)
        
        result: list[T] = []

        for elem in elems:
            tree_item = self.get_collection_item_by_value(elem)
            
            if tree_item is None:
                raise fbe.TemporaryFeedbackError("Not part of collection", elem)

            result.append(tree_item.value)

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
            return (AbstractAttribute.SORT_KEY_NONE_NUMBER + 1) * sign
        
        if self.has_collection():
            try:
                return tuple(
                    (
                        coll_item.sort_value
                        if (coll_item := self.get_collection_item_by_value(v)) is not None
                        else self.__class__.SORT_KEY_NONE_NUMBER
                    ) * sign
                    for v in values
                )
            except KeyError as e:
                raise RuntimeError(
                    f"Sort value for elem '{e.args[0]}' not found, which " +
                    f"should not happen."
                )
        
        return tuple(self._sort_key_singular(value, sign, self.value_type) for value in values)
    
    def is_empty(self, value: str) -> bool:
        return bool(self.from_str(value, None)) 




@dataclass(kw_only=True)
class StaticAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "static attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "static"
    TYPE_ID: ClassVar[int] = 0
    

    unique_value_per_list: bool
    
    _aliases: set[str] | None = field(init=False, default=None)
    
    def get_aliases(self) -> set[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            SAAT = TBL.StaticAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {SAAT.alias}
                    FROM {SAAT}
                    WHERE {SAAT.static_attribute_id} = {h|self.id}
                """)

                rows: S.ManyTableRowT = cursor.fetchall()

            self._aliases = {row[SAAT.alias] for row in rows}
        
        return self._aliases
    
    def get_collection(self) -> CollectionTreeT[T]:
        return []
    
    def get_collection_item_by_value(self, value: T) -> CollectionTreeItem[T] | None:
        return None
        

@dataclass(kw_only=True)
class TaskAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "task attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "task"
    TYPE_ID: ClassVar[int] = 1

    unique_value_per_list: bool

    _aliases: set[str] | None = field(init=False, default=None)
    _collection: CollectionTreeT[T] | None = field(init=False, default=None)
    _collection_item_lookup: dict[T, CollectionTreeItem[T]] = field(init=False, default=dict)  # type: ignore

    def get_aliases(self) -> set[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            SAAT = TBL.TaskAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {SAAT.alias}
                    FROM {SAAT}
                    WHERE {SAAT.task_attribute_id} = {h|self.id}
                """)

                rows: S.ManyTableRowT = cursor.fetchall()

            self._aliases = {row[SAAT.alias] for row in rows}
        
        return self._aliases
    
    def get_collection(self) -> CollectionTreeT[T]:
        if self._collection is None:
            h = queries.ArgHelper()
            TACNT = TBL.TaskAttributeCollectionNode
            TACNAT = TBL.TaskAttributeCollectionNodeAlias

            with queries.connected() as (conn, cursor):
                
                cursor.execute(f"""
                    SELECT 
                        n.*,
                        COALESCE(
                            JSON_ARRAYAGG(a.{TACNAT.alias}),
                            JSON_ARRAY()
                        ) AS {TACNT._aliases}
                    FROM {TACNT} n
                    LEFT JOIN {TACNAT} a
                        ON a.{TACNAT.task_attribute_collection_node_id} = n.{TACNT.id}
                    WHERE {TACNT.task_attribute_id} = {h|self.id}
                    GROUP BY n.{TACNT.id}
                """, h.steal())

            self._collection, self._collection_item_lookup = _generate_collection(cursor.fetchall(), TACNT)

        return self._collection
    
    def get_collection_item_by_value(self, value: T) -> CollectionTreeItem[T] | None:
        v = _normalize_collection_value(value)
        return self._collection_item_lookup.get(v, None)
        


class UserAttributeAliasReultT(TypedDict):
    alias: str

@dataclass(kw_only=True)
class UserAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "user attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "user"
    TYPE_ID: ClassVar[int] = 2

    _aliases: set[str] | None = field(init=False, default=None)
    _collection: CollectionTreeT[T] | None = field(init=False, default=None)
    _collection_item_lookup: dict[T, CollectionTreeItem[T]] = field(init=False, default=dict)  # type: ignore
    
    def get_aliases(self) -> set[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            SAAT = TBL.UserAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {SAAT.alias}
                    FROM {SAAT}
                    WHERE {SAAT.user_attribute_id} = {h|self.id}
                """)

                rows: S.ManyTableRowT = cursor.fetchall()

            self._aliases = {row[SAAT.alias] for row in rows}
        
        return self._aliases
    
    def get_collection(self) -> CollectionTreeT[T]:
        if self._collection is None:
            h = queries.ArgHelper()
            UACNT = TBL.UserAttributeCollectionNode
            UACNAT = TBL.UserAttributeCollectionNodeAlias

            with queries.connected() as (conn, cursor):
                
                cursor.execute(f"""
                    SELECT 
                        n.*,
                        COALESCE(
                            JSON_ARRAYAGG(a.{UACNAT.alias}),
                            JSON_ARRAY()
                        ) AS {UACNT._aliases}
                    FROM {UACNT} n
                    LEFT JOIN {UACNAT} a
                        ON a.{UACNAT.user_attribute_collection_node_id} = n.{UACNT.id}
                    WHERE {UACNT.user_attribute_id} = {h|self.id}
                    GROUP BY n.{UACNT.id}
                """, h.steal())

            self._collection, self._collection_item_lookup = _generate_collection(cursor.fetchall(), UACNT)

        return self._collection

    def get_collection_item_by_value(self, value: T) -> CollectionTreeItem[T] | None:
        v = _normalize_collection_value(value)
        return self._collection_item_lookup.get(v, None)
    

ATTRIBUTE_TYPES: Final[tuple[type[AbstractAttribute], ...]] = tuple(AbstractAttribute.__subclasses__())