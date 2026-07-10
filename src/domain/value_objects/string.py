import re
import string
import typing as t

from domain.errors import business

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


class BaseSingleStr:
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
        if isinstance(other, type(self)):
            return self._str == other._str

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._str)

    @property
    def value(self) -> str:
        return self._str

    @classmethod
    def _create(cls, s: str) -> t.Self:
        """Create an instance of this :class:`~t.Self` but skip all forms of validation. Only use previously validated input!"""
        self = super().__new__(cls)
        self._str = s

        return self


class RealStr(BaseSingleStr):
    """String wrapper to sanitize a string."""

    def __init__(self, s: str) -> None:
        s = _replace_whitespace_groups(s, " ", True)
        s = _replace_bad_chars(s)
        s = "".join(c for c in s if c.isprintable())

        if not s:
            raise EmptyStringError()

        if "``" in s:
            raise DoubleBacktickError()

        self._str = s


class NormStr(BaseSingleStr):
    """String wrapper to normalize a :class:`~RealStr`."""

    def __init__(self, s: str | RealStr) -> None:
        if isinstance(s, str):
            s = RealStr(s)

        self._str = s._str.casefold()


# Per definition in unicode 1 character map to at most 3 characters after casing operations
UNICODE_MAX_MULTIPLE_CASING: t.Final[int] = 3


class Str:
    """A string wrapper used inside the entire domain.

    It holds the raw, a :class:`~RealStr` and a :class:`~NormStr` version of the wrapped string.

    The length and str(...) is returned from the real version of the string, while equality and
    the hash is based off the norm version of the string.
    """

    _raw: str
    _real: RealStr | None
    _norm: NormStr | None

    def __init__(self, s: str) -> None:
        self._raw = s
        self._real = None
        self._norm = None

        self._validation()

    @classmethod
    def _create_from_real_and_norm(
        cls,
        real: RealStr,
        norm: NormStr,
    ) -> t.Self:
        """Create an instance of this :class:`~t.Self` but skip all forms of validation. Only use previously validated input!"""
        self = cls.__new__(cls)

        self._raw = real._str
        self._real = real
        self._norm = norm

        return self

    @property
    def raw(self) -> str:
        return self._raw

    @property
    def real(self) -> RealStr:
        if self._real is None:
            self._real = RealStr(self._raw)

        return self._real

    @property
    def norm(self) -> NormStr:
        if self._norm is None:
            self._norm = NormStr(self.real)

        return self._norm

    def _validation(self) -> None:
        pass

    def __len__(self):
        return len(self.real)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, type(self)):
            return NotImplemented

        return self.norm == value.norm

    def __hash__(self) -> int:
        return hash(self.norm)

    def __str__(self) -> str:
        return str(self.real)

    def requals(self, value: object) -> bool:
        if not isinstance(value, type(self)):
            return NotImplemented

        return self.real == value.real

    @classmethod
    def norm_unique(cls, iterable: t.Iterable[str], /) -> tuple[t.Self, ...]:
        mapping: dict[NormStr, Str] = {}

        for s in iterable:
            if isinstance(s, cls):
                store = s
            else:
                store = cls(s)  # type: ignore

            existing = mapping.get(store.norm)

            if existing is not None:
                raise business.DuplicateUniqueRequiredString(existing, store)

            mapping[store.norm] = store

        # Dict order is preserved
        return tuple(
            cls._create_from_real_and_norm(store.real, store.norm)
            for store in mapping.values()
        )

    @classmethod
    def raise_if_not_unique(cls, iterable: t.Iterable[t.Self]) -> None:
        seen: dict[NormStr, t.Self] = {}

        for elem in iterable:
            existing = seen.get(elem.norm)

            if existing is None:
                seen[elem.norm] = elem
            else:
                raise business.DuplicateUniqueRequiredString(existing, elem)

    @classmethod
    def sequences_requal(cls, a: t.Sequence[t.Self], b: t.Sequence[t.Self], /) -> bool:
        """Return True if the two specified sequences are exactly equal (their real part)."""

        return len(a) == len(b) and all(aa.real == bb.real for aa, bb in zip(a, b))
