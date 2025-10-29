import string
import typing as t
from abc import ABC, abstractmethod

type TupleOfOneOrMore[T] = tuple[T, *tuple[T, ...]]


class SqlString(ABC):
    @abstractmethod
    def _sql_str(self) -> str:
        pass


def validate_identifier(s: str) -> bool:
    if len(s) > 64:
        return False

    GOOD_CHARS = set(string.ascii_letters + string.digits + "_")

    return all(c in GOOD_CHARS for c in s)
