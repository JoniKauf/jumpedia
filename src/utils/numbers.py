from typing import Final


INT32_MIN: Final[int] = -(2**31)
INT32_MAX: Final[int] = 2**31 - 1

INT64_MIN: Final[int] = -(2**63)
INT64_MAX: Final[int] = 2**63 - 1


def is_int32(n: int, /):
    return INT32_MIN <= n <= INT32_MAX


def is_int64(n: int, /):
    return INT64_MIN <= n <= INT64_MAX
