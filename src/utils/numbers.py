

from typing import Final


MIN_INT32: Final[int] = -(2**31)
MAX_INT32: Final[int] = 2**31 - 1

def is_int32(n: int):
    return MIN_INT32 <= n <= MAX_INT32