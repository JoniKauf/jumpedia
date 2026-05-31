import typing as t
import re
import string

from domain import errors

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
    _real: RealStr | None
    _norm: NormStr | None

    @t.overload
    def __init__(self, s: str) -> None:
        pass

    @t.overload
    def __init__(self, *, _real: RealStr, _norm: NormStr) -> None:
        pass
    
    def __init__(
        self,
        s: str | None = None,
        *,
        _real: RealStr | None = None,
        _norm: NormStr | None = None,
    ) -> None:
        if s is not None:
            assert _real is None
            assert _norm is None

            self._raw = s
            self._real = None
            self._norm = None
            self._from_db = False

            self._validation()
        else:
            assert _real is not None
            assert _norm is not None

            self._raw = _real._str
            self._real = _real
            self._norm = _norm
            self._from_db = True

    @property
    def raw(self) -> str:
        return self._raw

    @property
    def real(self) -> RealStr:
        if self._real is None:
            self._real = RealStr(self._raw, _validate=(not self._from_db))

        return self._real

    @property
    def norm(self) -> NormStr:
        if self._norm is None:
            self._norm = NormStr(self.real)

        return self._norm

    def __len__(self):
        return len(self.real)

    def _validation(self) -> None:
        pass
    
    @classmethod
    def unique(cls, iterable: t.Iterable[str], /) -> tuple[t.Self, ...]:
        mapping: dict[NormStr, StrStore] = {}

        for store in iterable:
            store = cls(store)

            existing = mapping.get(store.norm)

            if existing is not None:
                raise errors.DuplicateUniqueRequiredString(existing, store)

            mapping[store.norm] = store

        # Dict order is preserved
        return tuple(cls(_real=store.real, _norm=store.norm) for store in mapping.values())
