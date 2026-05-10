import typing as t
import re
import string

from _adapters import cached_property

ONE_OR_MORE_WHITESPACE_PATTERN = re.compile(r"\s+", re.UNICODE)
IDENTIFIER_CHARS = set(string.ascii_letters + string.digits + "_")

BAD_CHAR_MAPPING = str.maketrans(
    {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"', "‟": '"'}
)

def _replace_whitespace_groups(s: str, repl: str, strip: bool = True) -> str:
    return re.sub(ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)


def _replace_bad_chars(s: str) -> str:
    return s.translate(BAD_CHAR_MAPPING)

class EmptyStringError(ValueError):
    pass


class DoubleBacktickError(ValueError):
    pass


class BaseStr:
    _str: str

    def __str__(self) -> str:
        return self._str
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._str!r})"

    def __len__(self) -> int:
        return len(self._str)
    
    def __bool__(self) -> t.Literal[True]:
        return True
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseStr):
            return self._str == other._str
        if isinstance(other, str):
            return self._str == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._str)
    
    @property
    def value(self) -> str:
        return self._str


class RealStr(BaseStr):
    def __init__(self, s: str, *, _validate: bool = True) -> None:
        super().__init__()

        if _validate:
            s = _replace_whitespace_groups(s, " ", True)
            s = _replace_bad_chars(s)
            s = "".join(c for c in s if c.isprintable())

            if not s:
                raise EmptyStringError()

            if "``" in s:
                raise DoubleBacktickError()

        self._str = s


class NormStr(BaseStr):
    @t.overload
    def __init__(self, s: str, *, _validate: bool = True) -> None:
        pass

    @t.overload
    def __init__(self, s: RealStr) -> None:
        pass

    def __init__(self, s: str | RealStr, *, _validate: bool = True) -> None:
        super().__init__()

        if not _validate:
            assert isinstance(s, str)
            self._str = s

            return

        if isinstance(s, str):
            s = RealStr(s)
        
        self._str = s._str.lower()


class StrStore:
    _s: str
    _validate: bool

    def __init__(self, s: str, *, _validate: bool = True) -> None:
        self._s = s
        self._validate = _validate

    @property
    def raw(self) -> str:
        return self._s
    
    @cached_property
    def real(self) -> RealStr:
        return RealStr(self._s, _validate=self._validate)
        
    @cached_property
    def norm(self) -> NormStr:
        return NormStr(self.real)

    @classmethod
    def unique(cls, iterable: t.Iterable[str], /) -> tuple[t.Self, ...]:
        mapping: dict[NormStr, RealStr] = {}

        for s in iterable:
            s = cls(s)

            existing_real = mapping.get(s.norm)

            if existing_real is not None:
                raise ValueError(s.real, existing_real)

            mapping[s.norm] = s.real

        # Dict order is preserved
        return tuple(cls(real.value, _validate=False) for real in mapping.values())