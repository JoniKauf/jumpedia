import hashlib
import re
import typing as t
import unicodedata

_ONE_OR_MORE_WHITESPACE_PATTERN: t.Final = re.compile(r"\s+", re.UNICODE)
_QUOTATION_MARKS_TRANS_TABLE: t.Final = str.maketrans(
    {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"', "‟": '"'}
)


class EmptyStringError(ValueError):
    pass


class DoubleBacktickError(ValueError):
    pass


class BaseStrWrapper[T: (str, bytes)]:
    _value: T

    def __str__(self) -> str:
        return str(self._value)

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
        s = self.clean_whitespace(s, " ", True)
        s = self.replace_quotation_marks(s)
        s = self.remove_non_printables(s)
        s = self.normalize_unicode_codepoints(s)

        self.validate_final_string(s)

        self._value = s

    @classmethod
    def clean_whitespace(cls, s: str, repl: str, strip: bool) -> str:
        return re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, repl, s.strip() if strip else s)

    @classmethod
    def replace_quotation_marks(cls, s: str) -> str:
        return s.translate(_QUOTATION_MARKS_TRANS_TABLE)

    @classmethod
    def remove_non_printables(cls, s: str) -> str:
        return "".join(c for c in s if c.isprintable())

    @classmethod
    def normalize_unicode_codepoints(cls, s: str) -> str:
        return unicodedata.normalize("NFC", s)

    @classmethod
    def validate_final_string(cls, s: str) -> None:
        if not s:
            raise EmptyStringError()

        if "``" in s:
            raise DoubleBacktickError()


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
    def _create_from_real_and_hash(
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
