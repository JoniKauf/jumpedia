from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
import decimal
import enum
import functools
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator, Protocol, Self, TypedDict, Union
import typing

import errors
from structures.attributes.collection import Collection

if TYPE_CHECKING:
    from structures.attributes.static_attribute import StaticAttribute
    from structures.attributes.task_attribute import TaskAttribute
    from structures.attributes.user_attribute import UserAttribute



type AnyAttributeT[T: AttributeValueTypeT] = StaticAttribute[T] | TaskAttribute[T] | UserAttribute[T]
type UniquenessAttributeT[T: AttributeValueTypeT] = UserAttribute[T]
type UniquenessExtendedAttributeT[T: AttributeValueTypeT] = StaticAttribute[T] | TaskAttribute[T]
type CollectionAttributeT[T: AttributeValueTypeT] = TaskAttribute[T] | UserAttribute[T]

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

    @property
    def literal_to_str_possible(self) -> bool:
        return self.type in LITERAL_TO_STR_POSSIBLE

    _attribute_value_types: ClassVar[list[Self]] = []
    _attribute_value_type_id_lookup: ClassVar[dict[int, Self]] = {}
    _attribute_value_type_name_lookup: ClassVar[dict[str, Self]] = {}
    _attribute_value_type_type_lookup: ClassVar[dict[str, Self]] = {}

    def __post_init__(self):
        for elem in AttributeValueType._attribute_value_types:
            if self.name == elem.name or self.id == elem.id or self.type == elem.type:
                raise AssertionError()
            
        AttributeValueType._attribute_value_types.append(self)
        AttributeValueType._attribute_value_type_id_lookup[self.id] = self
        AttributeValueType._attribute_value_type_name_lookup[self.name] = self
        AttributeValueType._attribute_value_type_type_lookup[self.type.__qualname__] = self

    def __hash__(self):
        return hash((self.id, self.name))
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(id={self.id!r}, name={self.name!r}, type={self.type!r}, literal_to_str_possible={self.literal_to_str_possible!r})'
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
        
    @classmethod
    def get_all(cls) -> list[Self]:
        return cls._attribute_value_types.copy()


AttributeValueType(1, 'boolean', bool)
AttributeValueType(2, 'integer', int)
AttributeValueType(3, 'decimal', Decimal)
AttributeValueType(4, 'time', dt.time)
AttributeValueType(5, 'date', dt.date)
AttributeValueType(6, 'date_and_time', dt.datetime)
AttributeValueType(7, 'timespan', dt.timedelta)
AttributeValueType(8, 'text_string', str)

AttributeValueTypeEnum = enum.Enum(
    'AttributeValueTypeEnum', [(avt.name, avt) for avt in AttributeValueType._attribute_value_types] + []
)

# Validate integrity
if AttributeValueTypeT.__value__.__args__ != tuple(vt.value.type for vt in AttributeValueTypeEnum):  # type: ignore
    raise RuntimeError("Enum does not equal type!!")


# Single point of truth is type so we can use type checking; data -> type doesn't work
type LiteralToStrPossibleT = bool | int | str
LITERAL_TO_STR_POSSIBLE = frozenset(typing.get_args(LiteralToStrPossibleT.__value__))

# Any of TYPES_LITERAL_ALLOWED or a list of any of TYPES_LITERAL_ALLOWED
type AttributeValueParseTypesT = LiteralToStrPossibleT | list[LiteralToStrPossibleT]
ATTRIBUTE_VALUE_PARSE_TYPES = LiteralToStrPossibleT.__value__ | list[LiteralToStrPossibleT.__value__]


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

        for subcls in cls.__subclasses__():
            subcls._value_mapping = cls._value_mapping.copy()
            subcls._name_mapping = cls._name_mapping.copy()
            subcls._init_cls()
            
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
    

@functools.total_ordering
class UniquenessExtended(Uniqueness):
    @classmethod
    def _init_cls(cls):
        cls._value_mapping = cls._value_mapping.copy()
        cls._name_mapping = cls._name_mapping.copy()

        cls.PER_LIST = cls('per_list', 2)

Uniqueness._init_cls()


UniquenessEnum: enum.Enum = enum.Enum(
    'UniquenessEnum', [(obj.name, obj) for obj in Uniqueness._value_mapping.values()]
)

UniquenessExtendedEnum = enum.Enum(
    'UniquenessEnum', [(obj.name, obj) for obj in UniquenessExtended._value_mapping.values()]
)

type AnyUniquenessT = Uniqueness | UniquenessExtended

def get_uniqueness_for_attribute_cls(attribute_cls: type[AnyAttributeT]):
    if issubclass(attribute_cls, UserAttribute):
        return Uniqueness
    
    return UniquenessExtended


@dataclass
class AttributeDataCache[T: AttributeValueTypeT]():
    aliases: frozenset[str] | None = None
    collection: Collection[T] | None = None

# number
NUMBER_MAX: Final[int] = 2 ** 63 - 1
NUMBER_MIN: Final[int] = -NUMBER_MAX - 1
DECIMAL_PRECISION: Final[int] = decimal.getcontext().prec
DECIMAL_INT_PART_MAX_LEN: Final[int] = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
DECIMAL_DEC_PART_MAX_LEN: Final[int] = DECIMAL_PRECISION - DECIMAL_INT_PART_MAX_LEN
DECIMAL_MAX_STR_LEN: Final[int] = DECIMAL_PRECISION if DECIMAL_DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1

# str
STR_MIN_LEN: Final[int] = 1
STR_MAX_LEN: Final[int] = 512

# Collection
COLLECTION_MAX_MEMORY: Final[int] = 1024 * 32
COLLECTION_MAX_ELEMS: Final[int] = 1024
COLLECTION_MAX_DEPTH: Final[int] = 16

# General
MAX_SYN_LEN: Final[int] = 32
MAX_ALIAS_COUNT: Final[int] = 32
MAX_COLLECTION_ALIASES: Final[int] = 7
MAX_SLOTS: Final[int] = 32
SORT_KEY_NONE_NUMBER: Final[int] = max(abs(NUMBER_MIN), abs(NUMBER_MAX)) + 1