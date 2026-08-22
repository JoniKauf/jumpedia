import hashlib
import re
import typing as t
import unicodedata

from jumpedia.domain.errors.business import DoubleBacktick, EmptyString

_ONE_OR_MORE_WHITESPACE_PATTERN: t.Final = re.compile(r"\s+", re.UNICODE)
_QUOTATION_MARKS_TRANS_TABLE: t.Final = str.maketrans(
    {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"', "‟": '"'}
)


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
        s = self.clean(
            s,
            clean_whitespace=True,
            replace_quotation_marks=True,
            remove_non_printables=True,
            normalize_unicode_codepoints=True,
            validate_final_string=True,
        )

        self._value = s

    @classmethod
    def clean(
        cls,
        s: str,
        *,
        clean_whitespace: bool,
        replace_quotation_marks: bool,
        remove_non_printables: bool,
        normalize_unicode_codepoints: bool,
        validate_final_string: bool,
    ) -> str:
        if clean_whitespace:
            s = re.sub(_ONE_OR_MORE_WHITESPACE_PATTERN, " ", s.strip())

        if replace_quotation_marks:
            s = s.translate(_QUOTATION_MARKS_TRANS_TABLE)

        if remove_non_printables:
            s = "".join(c for c in s if c.isprintable())

        if normalize_unicode_codepoints:
            s = unicodedata.normalize("NFC", s)

        if validate_final_string:
            if not s:
                raise EmptyString()
            if "``" in s:
                raise DoubleBacktick()

        return s


class NormHash(BaseStrWrapper[bytes]):
    """String wrapper to normalize and hash a :class:`~RealStr` for fast equality
    checks.
    """

    def __init__(self, s: str | RealStr) -> None:
        if isinstance(s, str):
            s = RealStr(s)

        self._value = self.process(s.value, normalize=True, hash=True)

    @t.overload
    @classmethod
    def process(
        cls,
        s: str,
        *,
        normalize: bool,
        hash: t.Literal[True],
    ) -> bytes:
        pass

    @t.overload
    @classmethod
    def process(
        cls,
        s: str,
        *,
        normalize: bool,
        hash: t.Literal[False],
    ) -> str:
        pass

    @classmethod
    def process(
        cls,
        s: str,
        *,
        normalize: bool = True,
        hash: bool = True,
    ) -> str | bytes:
        """Normalizes and/or hashes a string."""
        if normalize:
            s = s.casefold()

        if hash:
            return hashlib.sha256(s.encode("utf-8")).digest()

        return s


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
