import decimal
import enum
import typing as t
from dataclasses import dataclass
from decimal import Decimal

from ...utils import text

type SlotTypeT = (
    bool
    | int
    | Decimal
    |
    # dt.time | dt.date | dt.datetime | dt.timedelta |
    str
)


type_ = type

STR_MIN_LEN: t.Final[int] = 1
STR_MAX_LEN: t.Final[int] = 255

NUMBER_MAX: t.Final[int] = 2**63 - 1
NUMBER_MIN: t.Final[int] = -NUMBER_MAX - 1
DECIMAL_PRECISION: t.Final[int] = decimal.getcontext().prec
DECIMAL_INT_PART_MAX_LEN: t.Final[int] = max(len(str(NUMBER_MAX)), len(str(NUMBER_MIN)))
DECIMAL_DEC_PART_MAX_LEN: t.Final[int] = DECIMAL_PRECISION - DECIMAL_INT_PART_MAX_LEN
DECIMAL_MAX_STR_LEN: t.Final[int] = (
    DECIMAL_PRECISION if DECIMAL_DEC_PART_MAX_LEN <= 0 else DECIMAL_PRECISION + 1
)


def is_valid_number(v: object) -> bool:
    if isinstance(v, bool):
        return False

    if not isinstance(v, (int, Decimal)):
        return False

    return NUMBER_MIN <= v <= NUMBER_MAX


class SlotStr(text.RealStr):
    pass


@dataclass
class SlotType:
    id: int
    display_name: str
    type: type[SlotTypeT]

    _slot_types: t.ClassVar[list[t.Self]] = []
    _slot_type_id_lookup: t.ClassVar[dict[int, t.Self]] = {}
    _slot_type_type_lookup: t.ClassVar[dict[str, t.Self]] = {}

    @classmethod
    def _init(cls):
        cls.BOOL = SlotType(1, "boolean (true/false)", bool)
        cls.INT = SlotType(2, "integer", int)
        cls.DECIMAL = SlotType(3, "decimal", Decimal)
        cls.STR = SlotType(8, "text", str)

    def __post_init__(self):
        for elem in SlotType._slot_types:
            if (
                self.display_name == elem.display_name
                or self.id == elem.id
                or self.type == elem.type
            ):
                raise AssertionError()

        SlotType._slot_types.append(self)
        SlotType._slot_type_id_lookup[self.id] = self
        SlotType._slot_type_type_lookup[self.type.__qualname__] = self

    def __hash__(self):
        return hash((self.id, self.display_name))

    def __str__(self) -> str:
        return self.display_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, name={self.display_name!r}, type={self.type!r})"

    @classmethod
    def get_by_id(cls, id: int) -> t.Self:
        try:
            return cls._slot_type_id_lookup[id]
        except KeyError as e:
            raise LookupError(*e.args)

    @classmethod
    def get_by_type(cls, type: type) -> t.Self:
        try:
            return cls._slot_type_type_lookup[type.__qualname__]
        except KeyError as e:
            raise LookupError(*e.args)

    @classmethod
    def get_all(cls) -> list[t.Self]:
        return cls._slot_types.copy()

    def raw_to_slot(self, s: str) -> SlotStr:
        if not isinstance(s, str):
            raise TypeError()

        old_s, s = s, text.raw_to_real(s)

        if not s:
            raise feedbacks.temp(
                f"empty or only whitespace values like `{old_s}` are not allowed"
            )
        
        # String is definitely used most often, so check it first
        if issubclass(self.type, str):
            if not (STR_MIN_LEN <= len(s) <= STR_MAX_LEN):
                raise feedbacks.temp("String length out of bounds")

            return SlotStr(s)

        if issubclass(self.type, bool):
            s = s.lower()

            if s == "false":
                return SlotStr(False)
            if s == "true":
                return SlotStr(True)

            raise feedbacks.temp("Not a valid bool")

        elif issubclass(self.type, int):
            try:
                n = int(s)
            except Exception:
                raise feedbacks.temp("Invalid int")

            if not is_valid_number(n):
                raise feedbacks.temp("Number out of range")

            return SlotStr(s)

        elif issubclass(self.type, Decimal):
            try:
                n = Decimal(s)
                n = n.quantize(Decimal(f"1E-{DECIMAL_DEC_PART_MAX_LEN}"))
            except Exception:
                raise feedbacks.temp("Invalid decimal")

            if not is_valid_number(n):
                raise feedbacks.temp("Number out of range")

            return SlotStr(s)
        
        t.assert_never(self.type)

    def slot_to_type(self, s: SlotStr) -> SlotTypeT:
        return self.type(s)

    def slot_to_norm(self, s: SlotStr) -> SlotTypeT:
        if issubclass(self.type, str):
            return text.real_to_norm(s)
        
        return self.type(s)


SlotType._init()


SlotTypeEnum = enum.Enum(
    "SlotTypeEnum", [(avt.display_name, avt) for avt in SlotType._slot_types] + []
)

# Validate integrity
if SlotTypeT.__value__.__args__ != tuple(vt.value.type for vt in SlotTypeEnum):  # type: ignore
    raise RuntimeError("Enum does not equal type!!")
