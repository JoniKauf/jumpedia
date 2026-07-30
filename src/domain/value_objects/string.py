from hashlib import sha256
import hashlib
import re
import string
import typing as t
import unicodedata

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


class BaseStrWrapper[T: (str, bytes)]:
    _value: T

    def __str__(self) -> T:
        return self._value

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self._value!r})"

    def __len__(self) -> int:
        return len(self._value)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self._value == other._value

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    @property
    def value(self) -> T:
        return self._value

    @classmethod
    def _create(cls, s: T) -> t.Self:
        """Create an instance of this :class:`~t.Self` but skip all forms of validation. Only use previously validated input!"""
        self = super().__new__(cls)
        self._value = s

        return self

class RealStr(BaseStrWrapper[str]):
    """String wrapper to sanitize a string."""

    def __init__(self, s: str) -> None:
        s = _replace_whitespace_groups(s, " ", True)
        s = _replace_bad_chars(s)
        s = "".join(c for c in s if c.isprintable())
        s = unicodedata.normalize("NFC", s)

        if not s:
            raise EmptyStringError()

        if "``" in s:
            raise DoubleBacktickError()

        self._value = s


class NormHash(BaseStrWrapper[bytes]):
    """String wrapper to normalize and hash a :class:`~RealStr` for fast equality 
    checks.
    """

    def __init__(self, s: str | RealStr) -> None:
        if isinstance(s, str):
            s = RealStr(s)

        self._value = self.hash(self.normalize(s.value))

    @classmethod
    def normalize(cls, s: str) -> str:
        """Algorithm used to normalize strings."""
        return s.casefold()

    @classmethod
    def hash(cls, s: str) -> bytes:
        """Algorithm used for hashing strings after normalization."""
        return hashlib.sha256(s.encode("utf-8")).digest()


# Per definition in unicode 1 character maps to at most 3 characters after a casing operations
# So if we casefold our real str we can at most expect 3 times the length. That means
# every place where a real str is accepted in the DB, we need to have 3x the space for
# the norm str version and we are safe.
# I searched a while in the unicode docs to find this info but can't find it again LOL
UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING: t.Final[int] = 3


class Str:
    """A string wrapper used inside the entire domain.

    It holds a raw string, :class:`~RealStr` and :class:`~NormHash` of the wrapped string.

    The length and str(...) is returned from the real version of the string, while equality and
    the hash is based off the hash version of the string.
    """

    _raw: str
    _real: RealStr | None
    _hash: NormHash | None

    def __init__(self, s: str | RealStr) -> None:
        if isinstance(s, RealStr):
            self._raw = s.value
            self._real = s
        else:
            self._raw = s
            self._real = None  # Calculate lazily

        self._hash = None

        self._validation()

    @classmethod
    def _create_from_real_and_norm(
        cls,
        real: RealStr,
        hash: NormHash,
    ) -> t.Self:
        """Create an instance of this :class:`~t.Self` but skip all forms of validation. Only use previously validated input!"""
        self = cls.__new__(cls)

        self._raw = real._value
        self._real = real
        self._hash = hash

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
    def hash(self) -> NormHash:
        if self._hash is None:
            self._hash = NormHash(self.real)

        return self._hash

    def _validation(self) -> None:
        pass

    def __len__(self):
        return len(self.real)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, type(self)):
            return NotImplemented

        return self.hash == value.hash

    def __hash__(self) -> int:
        return hash(self.hash)

    def __str__(self) -> str:
        return str(self.real)

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({repr(self.real.value)})"

    def real_equals(self, value: object) -> bool:
        if not isinstance(value, type(self)):
            return NotImplemented

        return self.real == value.real

    @classmethod
    def sequence_real_equals(
        cls, a: t.Sequence[t.Self], b: t.Sequence[t.Self], /
    ) -> bool:
        """Return True if the two specified sequences are exactly equal (their real part)."""

        return len(a) == len(b) and all(aa.real == bb.real for aa, bb in zip(a, b))
