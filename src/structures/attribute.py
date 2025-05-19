from abc import ABC
import builtins
from dataclasses import dataclass, field
import enum
import datetime as dt
import functools
import json
import pickle
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Literal, Never, NotRequired, Optional, Self, TypedDict
from database import queries
from discordtools import errors, feedbackerrors as fbe
import re
from decimal import Decimal
import decimal
from utils import parsetools, text, timetools
from database import strong as S
from database.strong import Tables as T_

if TYPE_CHECKING:
    from structures.list import List
    from structures.task import Task

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

@dataclass(frozen=True)
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
    'AttributeValueTypeEnum', {avt.name: avt.type for avt in AttributeValueType._attribute_value_types}
)

if AttributeValueTypeT.__value__.__args__ != tuple(vt.value for vt in AttributeValueTypeEnum):  # type: ignore
    raise RuntimeError("Enum does not equal type!!")


@dataclass
class CollectionTreeItem[T]:
    value: T
    aliases: frozenset[T]
    sort_value: int
    nodes: 'CollectionTreeT[T]'
    root: 'CollectionTreeItem[T] | None' = None
type CollectionTreeT[T] = list[CollectionTreeItem[T]]



def _create_collection_lookup[T: AttributeValueTypeT](
    collection_tree: CollectionTreeT[T],
    lookup_ref: dict[T, CollectionTreeItem[T]]
) -> None:
    def recursive(tree: CollectionTreeT[T]) -> None:
        for item in tree:
            for syn in (norm_for_collection(item.value), *item.aliases):
                if syn in lookup_ref:
                    raise fbe.TemporaryFeedbackError("Same syn twice", syn)
            
            lookup_ref[item.value] = item

            recursive(item.nodes)
    
    recursive(collection_tree)


#------#   Attribute   #------#	

@dataclass(frozen=True, kw_only=True)
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
    SORT_KEY_LAST_NUMBER: ClassVar[int] = max(abs(NUMBER_MIN), abs(NUMBER_MAX)) + 1

    list: 'List'
    id: int 
    name: str
    value_type: AttributeValueType
    index: int
    min_slots: int
    max_slots: int
    unique_slots: bool

    @property
    def collection(self) -> CollectionTreeT[T]:
        raise NotImplementedError()
    
    @property
    def aliases(self) -> frozenset[str]:
        return frozenset()
            
    @property
    def syns(self) -> set[str]:
        return {self.name} | self.aliases
    
    @property
    def required(self) -> bool:
        return self.min_slots > 0
    
    @property
    def has_collection(self) -> bool:
        return bool(self.collection)
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity

    # --- Methods ---

    def __post_init__(self) -> None:
        if self.__class__ == AbstractAttribute:
            raise NotImplementedError()

        if self.has_collection:
            _create_collection_lookup(self.collection, self.collection_lookup)

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    @classmethod
    def generic_number_valid(cls, number: int | float | Decimal) -> None:
        if not (AbstractAttribute.NUMBER_MIN < number < AbstractAttribute.NUMBER_MAX):
            raise fbe.OutsideOfValidRange(number, AbstractAttribute.NUMBER_MIN, AbstractAttribute.NUMBER_MAX)
    
    @classmethod
    def _from_str_singular(cls, s: str, value_type: AttributeValueType[T]) -> T:
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
                result = result.quantize(Decimal(f"1E-{AbstractAttribute.DECIMAL_DEC_PART_MAX_LEN}"))
            except Exception:
                raise fbe.NotAProperValue("decimal", s)
            
            cls.generic_number_valid(result)
            
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
            
            result = text.fix_whitespace(s, " ", True)
        
        else:
            raise TypeError()
        
        return result  # type: ignore

    def from_str(self, s: str, value_type: AttributeValueType | None = None) -> builtins.list[T]:
        if not (s := s.strip()):
            return []
        
        try:
            loaded: str | list[Any] = parsetools.json_loads_safe(s, 1)
        except fbe.TemporaryFeedbackError:  # TODO if depth too big, custom feedback
            raise fbe.TemporaryFeedbackError 

        value_type = value_type or self.value_type

        converted: list[T] = []

        if isinstance(loaded, list):
            values = loaded
        else:
            values = [loaded]

        if not (self.min_slots <= (count := len(values)) <= self.max_slots):
            raise fbe.TemporaryFeedbackError("Count of values not between limits", self.min_slots, count, self.max_slots)
        
        for elem in values:
            if isinstance(elem, str):
                converted.append(self._from_str_singular(elem, value_type))
                continue

            if isinstance(elem, self.value_type.type) and issubclass(self.value_type.type, (bool, int)):
                converted.append(elem)
                continue
                
            raise fbe.TemporaryFeedbackError
        
        values = self._collection_conversion_if_needed(converted)

        if self.unique_slots:
            if len(values) != len(frozenset(values)):
                raise fbe.TemporaryFeedbackError("Values must be unique for this attribute")
            
        return values
        

    def to_str(self, obj: T) -> str:
        if isinstance(obj, (bool, int, Decimal, str)):
            return str(obj)
        
        if isinstance(obj, (dt.time, dt.date, dt.datetime)):
            return obj.isoformat()
        
        if isinstance(obj, (dt.timedelta)):
            return timetools.unparse_timedelta(obj)

    def _collection_conversion_if_needed(self, elems: Iterable[T]) -> builtins.list[T]:
        if not self.has_collection:
            return list(elems)
        
        result: list[T] = []

        for elem in elems:
            try:
                tree_item = self.collection_lookup[norm_for_collection(elem)]
            except KeyError:
                raise fbe.TemporaryFeedbackError("Not part of collection", elem)

            result.append(tree_item.value)

        return result
    
    def _sort_key_singular(self, value: T, sign: Literal[+1, -1]) -> int:
        vt: type[T] = self.value_type.type

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
            return (AbstractAttribute.SORT_KEY_LAST_NUMBER + 1) * sign
        
        if self.has_collection:
            try:
                return tuple(
                    self.collection_lookup[norm_for_collection(elem)].sort_value * sign for elem in values
                )
            except KeyError as e:
                raise RuntimeError(
                    f"Sort value for elem '{e.args[0]}' not found, which " +
                    f"should not happen."
                )
        
        return tuple(self._sort_key_singular(value, sign) for value in values)
    
    def is_empty(self, value: str) -> bool:
        return bool(self.from_str(value, None)) 



@dataclass(frozen=True, kw_only=True)
class StaticAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    unique_value_per_list: bool
    
    @property
    def collection(self) -> CollectionTreeT[T]:
        return ()

@dataclass(frozen=True, kw_only=True)
class TaskAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    unique_value_per_list: bool

    _collection: CollectionTreeT | None = field(init=False, default=None)

    @property
    def collection(self) -> CollectionTreeT[T]:
        if self._collection is None:
            h = queries.ArgHelper()
            TACNT = T_.TaskAttributeCollectionNode
            TACNTA = T_.TaskAttributeCollectionNodeAlias

            with queries.connected() as (conn, cursor):
                
                cursor.execute(f"""
                    SELECT 
                        n.*,
                        COALESCE(
                            JSON_ARRAYAGG(a.{TACNTA.alias}),
                            JSON_ARRAY()
                        ) AS {TACNT._aliases}
                    FROM {TACNT} n
                    LEFT JOIN {TACNTA} a
                        ON a.{TACNTA.task_attribute_collection_node_id} = n.{TACNT.id}
                    GROUP BY n.{TACNT.id}
                """)

                rows: list[S.TableResultT] = cursor.fetchall()

            lookup: dict[int, CollectionTreeItem] = {}
            root_of_nodes: dict[int, list[int]] = {}

            for row in rows:
                id = row[TACNT.id]
                root_id = row[TACNT.root_id]

                root_of_nodes.setdefault(root_id, []).append(id)
                lookup[id] = CollectionTreeItem(
                    value=row[TACNT.value],
                    aliases=frozenset(json.loads(row[TACNT._aliases])),
                    nodes=
                )
                

            result: CollectionTreeT = []

            for 

        return self._collection

    @property
    def aliases(self) -> frozenset[str]:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT alias
                FROM task_attribute_alias
                WHERE 
                    list_id = {h|self.list.id}
                    AND task_attribute_id = {h|self.id}
            """)

            result: list[TaskAttributeAliasReultT] = cursor.fetchall()

        return frozenset(row['alias'] for row in result)


    @classmethod
    def create(
        cls,
        list: 'List',
        bad_name: str,
        bad_aliases: Iterable[str],
        value_type: AttributeValueType[T],
        str_user_collection: str | None,
        min_slots: int,
        max_slots: int,
        unique_slots: bool,
        unique_value_per_list: bool,
    ) -> 'TaskAttribute':
        with list.edit_lock:
            name, aliases, (collection, pickled_collection), index = cls._create_attribute_basics(
                list=list,
                bad_name=bad_name,
                bad_aliases=bad_aliases,
                value_type=value_type,
                str_user_collection=str_user_collection,
                min_slots=min_slots,
                max_slots=max_slots,
            )

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO task_attribute (
                        list_id,
                        name,
                        value_type,
                        index,
                        collection,
                        min_slots,
                        max_slots,
                        unique_slots,
                        unique_value_per_list,
                    )
                    VALUES (
                        {h|list.id},
                        {h|name},
                        {h|value_type.id},
                        {h|index},
                        {h|pickled_collection},
                        {h|min_slots},
                        {h|max_slots},
                        {h|unique_slots},
                        {h|unique_value_per_list},
                    )
                """, h.steal())
                
                id: int = cursor.lastrowid,  # type: ignore

                cursor.execute(f"""
                    INSERT INTO task_attribute_alias (
                        task_attribute_id, list_id, alias
                    )
                    VALUES 
                        {','.join(f"({h|id}, {h|list.id}, {h|alias})" for alias in aliases)}
                """)

                return cls(
                    list=list,
                    id=id,
                    name=name,
                    index=index,
                    value_type=value_type,
                    collection=collection,
                    min_slots=min_slots,
                    max_slots=max_slots,
                    unique_slots=unique_slots,
                    unique_value_per_list=unique_value_per_list,
                ) 


class UserAttributeAliasReultT(TypedDict):
    alias: str

@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):

    @property
    def aliases(self) -> frozenset[str]:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT alias
                FROM user_attribute_alias
                WHERE 
                    list_id = {h|self.list.id}
                    AND user_attribute_id = {h|self.id}
            """)

            result: list[UserAttributeAliasReultT] = cursor.fetchall()

        return frozenset(row['alias'] for row in result)
    
    @classmethod
    def create(
        cls,
        list: 'List',
        bad_name: str,
        bad_aliases: Iterable[str],
        value_type: AttributeValueType[T],
        str_user_collection: str | None,
        min_slots: int,
        max_slots: int,
        unique_slots: bool
    ) -> 'UserAttribute':
        with list.edit_lock:
            name, aliases, (collection, pickled_collection), index = cls._create_attribute_basics(
                list=list,
                bad_name=bad_name,
                bad_aliases=bad_aliases,
                value_type=value_type,
                str_user_collection=str_user_collection,
                min_slots=min_slots,
                max_slots=max_slots
            )

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO user_attribute (
                        list_id,
                        name,
                        value_type,
                        index,
                        collection,
                        min_slots,
                        max_slots,
                        unique_slots
                    )
                    VALUES (
                        {h|list.id},
                        {h|name},
                        {h|value_type.id},
                        {h|index},
                        {h|pickled_collection},
                        {h|min_slots},
                        {h|max_slots},
                        {h|unique_slots}
                    )
                """, h.steal())
                
                id: int = cursor.lastrowid,  # type: ignore

                cursor.execute(f"""
                    INSERT INTO user_attribute_alias (
                        user_attribute_id, list_id, alias
                    )
                    VALUES 
                        {','.join(f"({h|id}, {h|list.id}, {h|alias})" for alias in aliases)}
                """)

                obj = cls(
                    list=list,
                    id=id,
                    name=name,
                    index=index,
                    value_type=value_type,
                    collection=collection,
                    min_slots=min_slots,
                    max_slots=max_slots,
                    unique_slots=unique_slots
                ) 

            return obj