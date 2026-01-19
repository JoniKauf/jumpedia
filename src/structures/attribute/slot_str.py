import decimal
import typing as t
from decimal import Decimal

from structures.jumpedia import JumpediaLimits
from utils import text

from .. import errors

if t.TYPE_CHECKING:
    from ..jumpedia import Jumpedia

type SlotTypeT = (bool | int | Decimal | str)
SLOT_TYPES = (bool, int, Decimal, str)

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
    def __new__(
        cls, s: text.RealStr, type: type[SlotTypeT], limits: JumpediaLimits
    ) -> t.Self:
        # String is definitely used most often, so check it first
        if issubclass(type, str):
            if len(s) > limits.attribute_task_value_slot_length_max:
                raise errors.InvalidSlotStrError(s, type)

            return super().__new__(cls, s, check=False)

        if issubclass(type, bool):
            s_low = s.lower()

            if s_low == "false":
                return super().__new__(cls, str(False), check=False)
            if s_low == "true":
                return super().__new__(cls, str(True), check=False)

            raise errors.InvalidSlotStrError(s, type)

        if issubclass(type, int):
            try:
                n = int(s)
            except Exception:
                raise errors.InvalidSlotStrError(s, type)

            if not is_valid_number(n):
                raise errors.InvalidSlotStrError(s, type)

            return super().__new__(cls, s, check=False)

        elif issubclass(type, Decimal):
            try:
                n = Decimal(s)
                n = n.quantize(Decimal(f"1E-{DECIMAL_DEC_PART_MAX_LEN}"))
            except Exception:
                raise errors.InvalidSlotStrError(s, type)

            if not is_valid_number(n):
                raise errors.InvalidSlotStrError(s, type)

            return super().__new__(cls, str(n), check=False)

        t.assert_never(type)

    def __init__(
        self, s: text.RealStr, type: type[SlotTypeT], limits: JumpediaLimits
    ) -> None:
        self.type = type
        self.limits = limits
        super().__init__()


def get_slot_type_by_id(id: int, /) -> type[SlotTypeT]:
    return SLOT_TYPES[id]


def get_slot_type_id(slot_type: type[SlotTypeT], /) -> int:
    return SLOT_TYPES.index(slot_type)
