from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum, auto
from functools import cached_property
import json
import sys
from typing import Any, Callable, ClassVar, Generic, Hashable, Iterable, Literal, Mapping, NamedTuple, Optional, Protocol, Self, TypeAlias, TypeGuard, TypeVar, TypedDict, Union, TYPE_CHECKING, cast, final, get_args
import re

from users.person import Person

if TYPE_CHECKING:
    from trickjump.trickjump import Trickjump


__init_module_done = False

_PATTERN = re.compile(r'[(?!^)([A-Z]+)]')

def pascal_to_snake(s: str):
    return re.sub(_PATTERN, r'_\1', s).lower()

class CollectionProtocol[VT](Protocol):
    COLLECTION: ClassVar[Mapping[Hashable, Self]]
    
    @property
    def value(self) -> VT:
        ...
        
    @classmethod
    def _init_cls(cls) -> None:
        ...
    


# --- Meta Classes ---

class Attr[VT](ABC):
    """
    Abstract base class for all attribute classes.
    An attribute class encapsulates data of a specific attribute,
    such that the attribute has more functionality, is easier to
    operate on and has its metadata is all stored in one place.
    """
    NAME: str
    ALIAS: frozenset[str]
    REQUIRED: bool
    USER_ATTR: Optional[bool]
    SECRET: bool

    def __init__(self, value: Optional[VT]):
        self.__instance_init_done = False
        self.value: Optional[VT] = value
        self.__instance_init_done = True

    def __setattr__(self, name: str, value: Any) -> None:
        if self.__instance_init_done:
            raise RuntimeError("Cannot change fields after initialization")
        return super().__setattr__(name, value)
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
    
    @classmethod
    def _init_cls(cls):
        cls.NAME = pascal_to_snake(cls.__name__)

        if __init_module_done:
            raise RuntimeError("Classes may only be initialized before the module is fully initialized!")
    
    @abstractmethod
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> Any:
        ...

    @classmethod
    @abstractmethod
    def get(cls, value: Self | VT | None) -> Self:
        """Always use this method to create/lookup objects."""
        ...

    
class AttrStr(Attr[str]):
    """
    A attribute that specifically has str as its value and
    implements the functionalities associated.
    """

    def __init__(self, value: Optional[str]):
        if self.value and not self.value.strip():
            super().__init__(None)
        else:
            super().__init__(value)


    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> tuple[int, ...]:
        if self.value is None: 
            return (((sys.maxunicode + 1) * sign),)
        return tuple(ord(char) * sign for char in self.value.casefold())
    
    @classmethod
    def get(cls, value: Self | str | None) -> Self:
        if value is None or isinstance(value, str):
            return cls(value)
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))


class AttrStrEntry(Attr[str]):
    COLLECTION: dict[Optional[str], Self] = {}

    def __init__(self, value: str | None, *, id: int, alias: frozenset[str] = frozenset()):
        if __init_module_done:
            raise RuntimeError(
                "No more objects of any collection can be created "
                "after the initialization of the module!"
            )
        
        self.id: int = id
        self.alias: frozenset[str] = alias

        super().__init__(value)    

    @classmethod
    def _init_cls(cls):
        cls.COLLECTION[None] = cls(None, id=-1)
        return super()._init_cls()
    
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> int:
        return self.id * sign
    
    @classmethod
    def get(cls, value: Self | str | None) -> Self:
        if value is None or isinstance(value, str):
            return cls.COLLECTION[value]
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))


class AttrDatetime(Attr[datetime]):
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> float:
        return (float("inf") if self.value is None else self.value.timestamp()) * sign
    
    @classmethod
    def get(cls, value: Self | datetime | None) -> Self:
        if value is None or isinstance(value, datetime):
            return cls(value)
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))


class AttrMultiValue[T: Attr](Attr[tuple[T, ...]]):
    """
    A collection of multiple instances of the same Attr.
    An empty collection is converted to None and all None
    entries are also removed on initialization.
    """
    def __init__(self, value: Optional[tuple[T, ...]], cls: type[T]):
        self.value = None if value is None else tuple(
            elem for elem in value if elem.value is not None
        )
        if not all(type(elem) == cls for elem in (value or ())):
            raise TypeError("cls should be the exact same type as all elements of value")
        self.cls = cls

        super().__init__(self.value)
    
    @cached_property
    def unpacked(self) -> tuple[Any, ...]:
        return tuple(elem.value for elem in (self.value or ()))
    
    def sort_key(self, sign: Literal[-1] | Literal[1] = +1, **kwargs: Any) -> tuple:
        if not self.value:
            return (self.cls.get(None).sort_key(sign),) * 2
        return tuple(elem.sort_key(sign) for elem in self.value)


# --- Attribute Classes ---

class Name(AttrStr):
    ALIAS: frozenset[str] = frozenset(["n"])
    REQUIRED = True
    USER_ATTR = None
    SECRET = False


class Location():
    outer: frozenset[Self] = field(kw_only=True, default=frozenset())
    tag: frozenset[str] = field(kw_only=True, default=frozenset())

    ALIAS: frozenset[str] = frozenset(["l", "loc", "k", "kd", "kingdom"])
    REQUIRED = True
    USER_ATTR = False
    SECRET = False
    

class Tier(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["t"])

    REQUIRED = True
    USER_ATTR = False
    SECRET = False


class Difficulty(AttrStrEntry):
    def __init__(self, value: Optional[str], *, tier: Tier, id: int, is_missing: bool = True, alias: frozenset[str] = frozenset()):
        self.tier: Tier = tier
        self.is_missing: bool = is_missing
        super().__init__(value, id=id, alias=alias)

    ALIAS: frozenset[str] = frozenset(["diff", "d"])
    REQUIRED = True
    USER_ATTR = False
    SECRET = False


class Server(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["s", "serv"])
    REQUIRED = True
    USER_ATTR = False
    SECRET = False


class Type(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["t", "ty", "typ"])
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


class Finder(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["f", "founder", "find", "found"])
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


class Taser(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["tas", "tased"])
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


class Prover(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["p", "prov", "proven"])
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


class FoundAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["fa", "f_a", "f_at"])
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


class TasedAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ta", "t_a", "t_at", "tas_at"])
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


class ProvenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["pa", "p_a", "p_at", "prov_at"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


class GivenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ga", "g_a", "g_at", "gave_at"])

    REQUIRED = False
    USER_ATTR = True
    SECRET = False


class Proof(AttrStr):
    ALIAS: frozenset[str] = frozenset(["prof", "prove", "proven"])

    REQUIRED = False
    USER_ATTR = True
    SECRET = False


class Link(AttrStr):
    def __init__(self, value: Optional[str], *, author: Person):
        super().__init__(value)
    author: Optional[str] = field(kw_only=True, default=None)
    ALIAS: frozenset[str] = frozenset(["l", "lnk", "clip", "video"])

    REQUIRED = True
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Extra(AttrMultiValueStr):
    ALIAS: frozenset[str] = frozenset(["ex", "e", "info", "i", "desc", "description", "data"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Thumbnail(AttrStr):
    ALIAS: frozenset[str] = frozenset(["tn", "thumb", "t_n", "th", "tnail"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = True

type __type = type

@dataclass(kw_only=True, init=False, unsafe_hash=True, slots=True)
class Attributes:
    name: Name
    location: Location
    difficulty: Difficulty

    tier: Tier = property(Tier.generate)  # type: ignore

    type: Type
    finder: Finder
    taser: Taser
    prover: Prover
    found_at: FoundAt
    tased_at: TasedAt
    proven_at: ProvenAt
    given_at: GivenAt
    proof: Proof
    server: Server
    link: Link
    extra: Extra
    thumbnail: Thumbnail


    def get(self, attr: __type[Attr] | Attr | str) -> Attr:
        if isinstance(attr, str):
            name = attr
        else:
            name = attr.NAME
        return getattr(self, name)

    def set(self, attr: __type[Attr] | Attr | str, value: Any) -> None:
        if isinstance(attr, str):
            cls = syn_to_cls(attr)
            name = attr
        else:
            cls = attr.__class__
            name = cls.NAME

        setattr(self, name, cls(value))

    def pop(self, attr: __type[Attr] | Attr | str) -> Attr:
        attr = self.get(attr)
        setattr(self, attr.NAME, attr.__class__(None))
        return attr
    

    def keys(self) -> tuple[str, ...]:
        return tuple(self.__slots__)


# Define instead of taking from dataclass so we keep literals and class type safety
ATTR_NAMES = ("name", "location", "difficulty", "tier", "type", "finder", "taser", "prover", "found_at", "tased_at", "proven_at", "given_at", "proof", "server", "link", "extra", "thumbnail")
ATTR_CLASSES = (Name, Location, Difficulty, Tier, Type, Finder, Taser, Prover, FoundAt, TasedAt, ProvenAt, GivenAt, Proof, Server, Link, Extra, Thumbnail)
ATTR_ITEMS = tuple(zip(ATTR_NAMES, ATTR_CLASSES, strict=True))

# --- IMPORTANT to check for integrity if any changes are made in the future ---


assert tuple(Attributes.__annotations__.items()) == tuple(ATTR_ITEMS) 


_ATTR_DCT: dict[str, type[Attr]] = {k: v for k, v in ATTR_ITEMS}

SYNONYM_COLLECTION: dict[str, type[Attr]] = {}  # fill out further down

def _cf(a: str, cf: bool):
    return a.casefold() if cf else a


def is_name(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in _ATTR_DCT

def is_alias(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) not in _ATTR_DCT and a in SYNONYM_COLLECTION

def is_syn(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in SYNONYM_COLLECTION

def syn_to_cls(a: str, cf: bool = True) -> type[Attr]:
    return SYNONYM_COLLECTION[_cf(a, cf)]

def syn_to_name(a: str, cf: bool = True) -> str:
    return SYNONYM_COLLECTION[_cf(a, cf)].NAME

def syn_to_aliases(a: str, cf: bool = True) -> frozenset[str]:
    return SYNONYM_COLLECTION[_cf(a, cf)].ALIAS


def to_classes(attrs: Iterable[str], cf: bool = True) -> tuple[type[Attr], ...]:
    return tuple(syn_to_cls(attr, cf) for attr in attrs)

def to_instances(attrs: Iterable[str], values: Iterable[str], cf: bool = True) -> tuple[Attr, ...]:
    return tuple(cls(val) for cls, val in zip(to_classes(attrs, cf), values, strict=True))




def _init_module():
    def recursively_iterate_subclasses(cls: type[Attr], do: Callable[[type[Attr]], None]):
        do(cls)

        for subclass in cls.__subclasses__():
            recursively_iterate_subclasses(subclass, do)
            

    recursively_iterate_subclasses(Attr, lambda cls: cls._init_cls())
    recursively_iterate_subclasses(Attr, lambda cls: cls._secondary_init_cls())


_init_module()


# all in all good codi but want to play bsso uwuwuwuwuwuwuwuuwuwuwuuwuwuwuuwuwuwuwuwuwuwuw
# Thank you for the review my bf  - Joni