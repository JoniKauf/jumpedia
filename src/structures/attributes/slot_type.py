import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
import decimal
import enum
import functools
import re
from typing import ClassVar, Final, Self, assert_never
import typing
from discordtools import messaging as msg
from errors.feedback import feedbacks
from utils import parsetools, text


type SlotTypeT = (
    bool | int | Decimal | 
    dt.time | dt.date | dt.datetime | dt.timedelta | 
    str
)


type_ = type

STR_MIN_LEN: Final[int] = 1
STR_MAX_LEN: Final[int] = 512

NUMBER_MAX: Final[int] = 2 ** 63 - 1
NUMBER_MIN: Final[int] = -NUMBER_MAX - 1
DECIMAL_PRECISION: Final[int] = decimal.getcontext().prec
DECIMAL_INT_PART_MAX_LEN: Final[int] = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
DECIMAL_DEC_PART_MAX_LEN: Final[int] = DECIMAL_PRECISION - DECIMAL_INT_PART_MAX_LEN
DECIMAL_MAX_STR_LEN: Final[int] = DECIMAL_PRECISION if DECIMAL_DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1

_DATE_ALTERNATIVE_DELIMITERS_PATTERN = re.compile(r'[/.]')

def is_valid_number(v: object) -> bool:
    if isinstance(v, bool):
        return False
    
    if not isinstance(v, (int, Decimal)):
        return False
    
    return NUMBER_MIN <= v <= NUMBER_MAX

def is_valid_str(v: object) -> bool:
    if not isinstance(v, str):
        return False
    
    return STR_MIN_LEN <= len(v) <= STR_MAX_LEN


@dataclass
class SlotType[T: SlotTypeT]:
    id: int
    name: str
    type: type[T]

    @property
    def literal_to_str_possible(self) -> bool:
        return self.type in LITERAL_TO_STR_POSSIBLE

    _slot_types: ClassVar[list[Self]] = []
    _slot_type_id_lookup: ClassVar[dict[int, Self]] = {}
    _slot_type_name_lookup: ClassVar[dict[str, Self]] = {}
    _slot_type_type_lookup: ClassVar[dict[str, Self]] = {}

    def __post_init__(self):
        for elem in SlotType._slot_types:
            if self.name == elem.name or self.id == elem.id or self.type == elem.type:
                raise AssertionError()
            
        SlotType._slot_types.append(self)
        SlotType._slot_type_id_lookup[self.id] = self
        SlotType._slot_type_name_lookup[self.name] = self
        SlotType._slot_type_type_lookup[self.type.__qualname__] = self

    def __hash__(self):
        return hash((self.id, self.name))
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(id={self.id!r}, name={self.name!r}, type={self.type!r}, literal_to_str_possible={self.literal_to_str_possible!r})'
    
    @classmethod
    def get_by_id(cls, id: int) -> Self:
        try:
            return cls._slot_type_id_lookup[id]
        except KeyError as e:
            raise LookupError(*e.args)
        
    @classmethod
    def get_by_name(cls, name: str) -> Self:
        try:
            return cls._slot_type_name_lookup[name]
        except KeyError as e:
            raise LookupError(*e.args)
        
    @classmethod
    def get_by_type(cls, type: type_[T]) -> 'SlotType[T]':
        try:
            return cls._slot_type_type_lookup[type.__qualname__]
        except KeyError as e:
            raise LookupError(*e.args)
        
    @classmethod
    def get_all(cls) -> list[Self]:
        return cls._slot_types.copy()
    
    @functools.lru_cache(maxsize=1024, typed=True)
    def norm(self, value: T) -> T:
        if type(value) != self.type:
            raise ValueError
        
        if issubclass(self.type, str):
            return text.norm(value)  # type: ignore
        
        return value

    def from_raw_str(self, s: str) -> T:
        old_s, s = s, text.sanitize(s)
        
        if not s:
            raise feedbacks.temp(f"empty or only whitespace values like {msg.code(old_s)} are not allowed")
        
        if issubclass(self.type, bool):
            s = s.lower()

            if s == "false":
                return False  # type: ignore
            if s == "true":
                return True  # type: ignore
            
            raise feedbacks.temp("Not a valid bool")
        
        elif issubclass(self.type, int):
            try:
                n = int(s)
            except Exception:
                raise feedbacks.temp("Invalid int")
            
            if not is_valid_number(n):
                raise feedbacks.temp("Number out of range")

            return n  # type: ignore
    
        elif issubclass(self.type, Decimal):
            try:
                n = Decimal(s)
                n = n.quantize(Decimal(f"1E-{DECIMAL_DEC_PART_MAX_LEN}"))
            except Exception:
                raise feedbacks.temp("Invalid decimal")
            
            if not is_valid_number(n):
                raise feedbacks.temp("Number out of range")
            
            return n  # type: ignore
            
        elif issubclass(self.type, (dt.time, dt.date, dt.datetime)):
            # If a date is in the type
            s = re.sub(_DATE_ALTERNATIVE_DELIMITERS_PATTERN, '-', s)
            
            try:
                dt.date.fromisoformat
                timed = self.type.fromisoformat(s)
            except Exception:
                raise feedbacks.temp("Invalid format for time/date/datetime")
                
            if not isinstance(timed, (dt.time, dt.datetime)):
                return timed
                
            if timed.tzinfo is None:
                timed = timed.replace(tzinfo=dt.timezone.utc)
            
            if isinstance(timed, dt.time):
                datetime = dt.datetime.combine(dt.date.today(), timed, timed.tzinfo)
                return datetime.astimezone(dt.timezone.utc).time()  # type: ignore
            
            return timed.astimezone(dt.timezone.utc)

        if issubclass(self.type, dt.timedelta):
            try:
                return parsetools.parse_timedelta(s)  # type: ignore
            except ValueError:
                raise feedbacks.temp("Invalid timedelta format")

        if issubclass(self.type, str):
            if not is_valid_str(s):
                raise feedbacks.temp("String length out of bounds")
            
            return s  # type: ignore

        assert_never(self.type)

    
    def to_str(self, o: T) -> str:
        if isinstance(o, str):
            return o
    
        if isinstance(o, bool | int | Decimal):
            return str(o)
    
        if isinstance(o, dt.time | dt.date | dt.datetime):
            return o.isoformat()
    
        if isinstance(o, dt.timedelta):
            return str(round(o.total_seconds(), 4))
    
        assert_never(o)
 
 
    def from_clean_str(self, s: str) -> T:
        if issubclass(self.type, str | bool | int | Decimal):
            return self.type(s)
    
        if issubclass(self.type, dt.time | dt.date | dt.datetime):
            return self.type.fromisoformat(s)
    
        if issubclass(self.type, dt.timedelta):
            return self.type(seconds=round(float(s), 4))
        
        assert_never(self.type)


SlotType(1, 'boolean', bool)
SlotType(2, 'integer', int)
SlotType(3, 'decimal', Decimal)
SlotType(4, 'time', dt.time)
SlotType(5, 'date', dt.date)
SlotType(6, 'date_and_time', dt.datetime)
SlotType(7, 'timespan', dt.timedelta)
SlotType(8, 'text_string', str)

AttributeValueTypeEnum = enum.Enum(
    'AttributeValueTypeEnum', [(avt.name, avt) for avt in SlotType._slot_types] + []
)

# Validate integrity
if SlotTypeT.__value__.__args__ != tuple(vt.value.type for vt in AttributeValueTypeEnum):  # type: ignore
    raise RuntimeError("Enum does not equal type!!")

# Single point of truth is type so we can use type checking; data -> type doesn't work
type LiteralToStrPossibleT = bool | int | str
LITERAL_TO_STR_POSSIBLE = (bool, int, str)


if typing.get_args(LiteralToStrPossibleT.__value__) != LITERAL_TO_STR_POSSIBLE:
    raise RuntimeError()
