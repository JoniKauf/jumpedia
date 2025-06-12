from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
import decimal
import enum
from typing import TYPE_CHECKING, Any, ClassVar, Final, Protocol, Self

from structures.attributes.collection import Collection

if TYPE_CHECKING:
    from structures.attributes.static_attribute import StaticAttribute
    from structures.attributes.task_attribute import TaskAttribute
    from structures.attributes.user_attribute import UserAttribute



type AnyAttributeT[T: AttributeValueTypeT] = StaticAttribute[T] | TaskAttribute[T] | UserAttribute[T]

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
    _attribute_value_type_id_lookup: dict[int, Self] = {}
    _attribute_value_type_name_lookup: dict[str, Self] = {}
    _attribute_value_type_type_lookup: dict[str, Self] = {}

    def __hash__(self):
        return hash((self.id, self.name, self.type.__qualname__))
    
    def __post_init__(self):
        for elem in AttributeValueType._attribute_value_types:
            if self.name == elem.name or self.id == elem.id or self.type == elem.type:
                raise AssertionError()
            
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

AttributeValueType(1, 'boolean (true/false)', bool)
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


class _PrivateAliasesFieldProtocol(Protocol):
    _aliases: Final[frozenset[str] | None]

def _post_set_aliases(obj: _PrivateAliasesFieldProtocol, aliases: frozenset[str]) -> None:
    object.__setattr__(obj, '_aliases', aliases)


class _PrivateCollectionFieldProtocol(Protocol):
    _collection: Final[Collection[AttributeValueTypeT, Any] | None]


def _post_set_collection(obj: _PrivateCollectionFieldProtocol, collection: Collection[AttributeValueTypeT, Any]) -> None:
    object.__setattr__(obj, '_collection', collection)
    

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