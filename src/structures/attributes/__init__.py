from abc import abstractmethod
import builtins
from dataclasses import dataclass, field
import datetime as dt
from decimal import Decimal
import decimal
import enum
import functools
import json
import pickle
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, NamedTuple, Self, final
import typing

from database import queries, typed
from discordtools import messaging
import errors
from errors.feedback import feedbacks
from structures.attributes import slot_type
from structures.attributes import collection
from structures.attributes.slot_type import LiteralToStrPossibleT, SlotType, SlotTypeT
from structures.attributes.collection import BaseCollectionAttribute, Collection, CollectionNode, CollectionNodesT
from structures.base_structure import BaseStructure
from structures.list import List
from utils import numbers, parsetools, text
if TYPE_CHECKING:
    from structures.attributes.static_attribute import StaticAttribute
    from structures.attributes.task_attribute import TaskAttribute
    from structures.attributes.user_attribute import UserAttribute



type AnyAttributeT[T: SlotTypeT] = StaticAttribute[T] | TaskAttribute[T] | UserAttribute[T]
ANY_ATTRIBUTE = (StaticAttribute, TaskAttribute, UserAttribute)

@final
@functools.total_ordering
class Uniqueness:
    _value_mapping: dict[int, Self] = {}
    _name_mapping: dict[str, Self] = {}

    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value

        if self.value in self.__class__._value_mapping:
            raise RuntimeError
        
        if self.name in self.__class__._name_mapping:
            raise RuntimeError
        
        self.__class__._value_mapping[value] = self
        self.__class__._name_mapping[name] = self

    @classmethod
    def _init_cls(cls):
        cls.NONE = cls('none', 0)
        cls.PER_VALUE = cls('per_value', 1)
        cls.PER_LIST = cls('per_list', 2)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Uniqueness) and self.value == other.value:
            return True
        
        return NotImplemented
    
    def __lt__(self, other: Any):
        if isinstance(other, Uniqueness):
            return self.value < other.value
        
        return NotImplemented
    
    def __bool__(self) -> bool:
        return bool(self.value)
    
    @classmethod
    def get_by_value(cls, value: int) -> Self:
        return cls._value_mapping[value]
    
    @classmethod
    def get_by_name(cls, name: str) -> Self:
        return cls._name_mapping[name]

Uniqueness._init_cls()

UniquenessEnum: enum.Enum = enum.Enum(
    'UniquenessEnum', [(obj.name, obj) for obj in Uniqueness._value_mapping.values()]
)

@dataclass
class AttributeDataCache[T: SlotTypeT]:
    _aliases: frozenset[str] | None = None
    _collection: Collection[T] | None = None

    @property
    def aliases(self) -> frozenset[str] | None:
        return self._aliases
    
    @aliases.setter
    def aliases(self, value: frozenset[str]) -> None:
        self._aliases = value

    @property
    def collection(self) -> Collection[T] | None:
        return self._collection
    
    @collection.setter
    def collection(self, value: Collection[T]) -> None:
        self._collection = value


type RawCollectionNodesT[T: SlotTypeT] = frozenset[RawCollectionNode[T]]

class RawCollectionNode[T: SlotTypeT](NamedTuple):
    value: T
    aliases: frozenset[T]
    sort_value: int
    children: RawCollectionNodesT[T]

# General
MIN_SYN_LEN: Final[int] = 1
MAX_SYN_LEN: Final[int] = 32
MAX_ALIAS_COUNT: Final[int] = 32
MAX_COLLECTION_ALIASES: Final[int] = 7
MAX_SLOTS: Final[int] = 32
SORT_KEY_NONE_NUMBER: Final[int] = max(abs(slot_type.NUMBER_MIN), abs(slot_type.NUMBER_MAX)) + 1


# Any of TYPES_LITERAL_ALLOWED or a list of any of TYPES_LITERAL_ALLOWED
type AttributeValueParseTypesT = LiteralToStrPossibleT | list[LiteralToStrPossibleT]
ATTRIBUTE_VALUE_PARSE_TYPES = (bool, int, str, [bool, int, str])

# Checking ATTRIBUTE_VALUE_PARSE_TYPES is too much effort and hard to generalize
# Just make sure it stays consistent when changing one



@dataclass(frozen=True)
class AttributeTables:
    attribute: type[typed.BaseAttribute]
    attribute_alias: type[typed.BaseAttributeAlias]


@dataclass(frozen=True)
class NonStaticAttributeTables(AttributeTables):
    attribute_collection_node: type[typed.BaseCollectionAttributeCollectionNode]
    attribute_collection_node_alias: type[typed.BaseCollectionAttributeCollectionNodeAlias]
    attribute_task_value: type[typed.BaseAttributeTaskValue]
    

@dataclass(frozen=True, kw_only=True)
class BaseAttribute[T: SlotTypeT](BaseStructure):
    __structure_name__ = "base attribute"
    tables: ClassVar[AttributeTables]
    allow_min_slots_on_creation: ClassVar[bool] = False
    deletable: ClassVar[bool] = True

    list: 'List'
    id: int 
    name: str
    slot_type: SlotType[T]
    position: int
    min_slots: int
    max_slots: int
    uniqueness: Uniqueness

    value_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=collection.MAX_DEPTH,
        strict_type=ATTRIBUTE_VALUE_PARSE_TYPES
    )
    
    _cache: AttributeDataCache[T] = field(init=False, default_factory=AttributeDataCache)

    @property
    def identity(self) -> tuple[int, ...]:
        return (ANY_ATTRIBUTE.index(self.__class__), self.id) + self.list.identity
    
    @property
    def required(self) -> bool:
        return self.min_slots > 0
    
    # --- Methods ---

    def __post_init__(self) -> None:
        if self.__class__ == BaseAttribute:
            raise RuntimeError()

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    def get_syns(self) -> set[str]:
        return {self.name} | self.get_aliases()
    
    def get_aliases(self) -> frozenset[str]:
        assert isinstance(self, ANY_ATTRIBUTE)

        if self._cache.aliases is not None:
            return self._cache.aliases
        
        TblAlias = self.__class__.tables.attribute_alias

        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT {TblAlias.alias}
                FROM {TblAlias}
                WHERE {TblAlias.attribute_id} = {arg(self.id)}
            """)

            rows = c.fetchall(TblAlias)
        
        self._cache.aliases = aliases = frozenset(row.alias for row in rows)

        return aliases
    
    def get_collection(self) -> Collection[T]:
        return Collection(
            attribute=self,
            top_nodes=frozenset(),
            normed_syn_to_node=MappingProxyType({})
        )

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
    def general_from_str[T_: AttributeValueParseTypesT](cls, s: str, parser: parsetools.SafeJsonParser[T_]) -> T_:
        try:
            return parser.loads(s)
        except json.JSONDecodeError as e:
            raise feedbacks.temp(f"Not valid json at ...{e.msg[e.pos:e.pos + 10]}...")
        except RecursionError as e:
            raise feedbacks.temp(f"Max depth for json exceeded")
        except TypeError as e:
            raise feedbacks.temp(f"object {messaging.code(e.args[0])} is not of type {messaging.code(e.args[1])}")
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
            return (SORT_KEY_NONE_NUMBER + 1) * sign,
        
        collection = self.get_collection()

        if collection.is_empty:
            return tuple(
                self._sort_key_singular(value, sign, self.slot_type) 
                for value in v
            )

        return tuple((
                coll_item.sort_value
                if (coll_item := collection.lookup_node(slot, None)) is not None
                else SORT_KEY_NONE_NUMBER
            ) * sign
            for slot in v
        )

    def is_valid_value(self, value: builtins.list) -> bool:
        if not isinstance(value, list):
            return False
        
        return all(self.slot_type.is_valid_slot(slot) for slot in value)