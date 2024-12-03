from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum, auto
import json
import sys
from typing import Any, ClassVar, Generic, Hashable, Iterable, Literal, Mapping, NamedTuple, Optional, Self, TypeAlias, TypeGuard, TypeVar, TypedDict, Union, TYPE_CHECKING, cast, final, get_args

if TYPE_CHECKING:
    from trickjump.trickjump import Trickjump


_init_module_done = False

_id = id

# --- Meta Classes ---
 
@dataclass(unsafe_hash=True)
class Attr[VT](ABC):
    """
    Abstract base class for all attribute classes.
    An attribute class encapsulates data of a specific attribute,
    such that the attribute has more functionality, is easier to
    operate on and has its metadata all stored in one place.
    """
    value: Optional[VT]

    NAME: ClassVar[str]
    ALIAS: ClassVar[frozenset[str]]

    REQUIRED: ClassVar[bool]
    USER_ATTR: ClassVar[bool | None]
    SECRET: ClassVar[bool]

    @classmethod
    def _init_cls(cls, *args, **kwargs):
        pass
    
    @abstractmethod
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> Any:
        ...

    @classmethod
    @abstractmethod
    def get(cls, value: Self | VT | None) -> Self:
        """Always use this method to create/lookup objects."""
        ...


@dataclass(unsafe_hash=True)
class MultiValueMixin:
    value: Optional[tuple[Attr, ...]]
    unpacked: Optional[tuple[Any, ...]] = field(init=False) 
    
    def __post_init__(self):
        if not self.value:
            self.value = None
        
        self.unpacked = (
            None if self.value is None else
            tuple(elem.value for elem in self.value)
        )

    
@dataclass(unsafe_hash=True)
class AttrStr[VT = str](Attr[VT]):
    value: Optional[str]

    def __post_init__(self):
        if self.value and not self.value.strip():
            self.value = None

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
        
        raise TypeError("Unexpected type: ", type(value))


@dataclass(unsafe_hash=True)
class AttrMultiValueStr(MultiValueMixin, AttrStr[tuple[AttrStr, ...]]):
    value: Optional[tuple[AttrStr, ...]]

    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> tuple[tuple[int, ...], ...]:
        # Sort None as very last element
        if self.value is None:
            return ((sys.maxunicode + 2,),)
        return tuple(elem.sort_key(sign) for elem in self.value)
    
    @classmethod
    def get(cls, value: Self | tuple[AttrStr | str | None, ...] | str | None) -> Self:
        if value is None:
            return cls(value)
        if isinstance(value, tuple):
            return cls(tuple(AttrStr.get(v) for v in value))
        if isinstance(value, str):
            return cls((AttrStr.get(value),))
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type: ", type(value))


@dataclass(unsafe_hash=True)
class AttrCollection[VT: Hashable = str](Attr[VT]):
    alias: frozenset[str] = frozenset()

    ALL: ClassVar[dict[Hashable, Self]]
    VALUES: ClassVar[dict[Hashable, Any]]

    def __post_init__(self):
        if _init_module_done:
            raise RuntimeError(
                "No more objects of any collection attr can be created "
                "after the initialization of the module!"
            )
        
    @classmethod
    @abstractmethod
    def _init_cls(cls) -> None:
        ...

    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> int:
        return self.__class__.VALUES[self.value] * sign
    
    @classmethod
    def get(cls, value: Self | str | None) -> Self:
        if value is None or isinstance(value, str):
            return cls.ALL[value]
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type: ", type(value))


@dataclass(unsafe_hash=True)
class AttrMultiValueCollectionBase(MultiValueMixin, AttrCollection[tuple[AttrCollection, ...]]):
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> tuple[int, ...]:
        if self.value is None:
            return (len(self.__class__.VALUES),) * sign
        return tuple(self.__class__.VALUES[elem.value] * sign for elem in self.value)
    
    @classmethod
    def get(cls, value: Self | tuple[AttrCollection | str | None, ...] | str | None) -> Self:
        if value is None:
            return cls(value)
        if isinstance(value, tuple):
            return cls(tuple(AttrCollection.get(v) for v in value))
        if isinstance(value, str):
            return cls((AttrCollection.get(value),))
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type: ", type(value))


@dataclass(unsafe_hash=True)
class AttrDatetimeBase(Attr[datetime]):
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> float:
        return (float("inf") if self.value is None else self.value.timestamp()) * sign



# --- Attribute Classes ---

@dataclass(unsafe_hash=True)
class Name(AttrStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["n"])

    REQUIRED = True
    USER_ATTR = None
    SECRET = False


@dataclass(unsafe_hash=True)
class Location(AttrCollection):
    parent: frozenset[Self] = frozenset()
    tag: frozenset[str] = frozenset()

    ALIAS: ClassVar[frozenset[str]] = frozenset(["l", "loc", "k", "kd", "kingdom"])

    REQUIRED = True
    USER_ATTR = False
    SECRET = False

    PathT = ClassVar[list[Union['Location', 'PathT']]]  # recursive

    def get_all_paths(self) -> PathT:
        def walk(loc: Self) -> Location.PathT:
            if not loc.parent:
                return [loc]
            else:
                paths = []
                for inner_loc in loc.parent:
                    for path in walk(inner_loc):
                        paths.append([loc] + (path if isinstance(path, list) else [path]))
                return paths
        
        return walk(self)
    

@dataclass(unsafe_hash=True)
class Tier(AttrCollection):
    alias: frozenset[str] = frozenset()

    ALIAS: ClassVar[frozenset[str]] = frozenset()

    REQUIRED = True
    USER_ATTR = False
    SECRET = False
    

@dataclass(unsafe_hash=True, kw_only=True)
class Difficulty(AttrCollection):
    alias: frozenset[str] = frozenset()
    tier: Tier
    is_missing: bool = True

    ALIAS: ClassVar[frozenset[str]] = frozenset(["diff", "d"])

    REQUIRED = True
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Server(AttrCollection):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["s", "serv"])

    REQUIRED = True
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Type(AttrStr):
    # TODO:
    # - Collection
    # - required = True

    ALIAS: ClassVar[frozenset[str]] = frozenset(["t", "ty", "typ"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Finder(AttrMultiValueStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["f", "founder", "find", "found"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Taser(AttrMultiValueStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["tas", "tased"])
    
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Prover(AttrMultiValueStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["p", "prov", "proven"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class FoundAt(AttrDatetimeBase):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["fa", "f_a", "f_at"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class TasedAt(AttrDatetimeBase):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["ta", "t_a", "t_at", "tas_at"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class ProvenAt(AttrDatetimeBase):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["pa", "p_a", "p_at", "prov_at"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class GivenAt(AttrDatetimeBase):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["ga", "g_a", "g_at", "gave_at"])

    REQUIRED = False
    USER_ATTR = True
    SECRET = False


@dataclass(unsafe_hash=True)
class Proof(AttrStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["prof", "prove", "proven"])

    REQUIRED = False
    USER_ATTR = True
    SECRET = False


@dataclass(unsafe_hash=True)
class Link(AttrMultiValueStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["l", "lnk", "clip", "video"])

    REQUIRED = True
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Extra(AttrMultiValueStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["ex", "e", "info", "i", "desc", "description", "data"])

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Thumbnail(AttrStr):
    ALIAS: ClassVar[frozenset[str]] = frozenset(["tn", "thumb", "t_n", "th", "tnail"])

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

SYNONYM_LOOKUP: dict[str, type[Attr]] = {}  # fill out further down

def _cf(a: str, cf: bool):
    return a.casefold() if cf else a


def is_name(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in _ATTR_DCT

def is_alias(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) not in _ATTR_DCT and a in SYNONYM_LOOKUP

def is_syn(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in SYNONYM_LOOKUP

def syn_to_cls(a: str, cf: bool = True) -> type[Attr]:
    return SYNONYM_LOOKUP[_cf(a, cf)]

def syn_to_name(a: str, cf: bool = True) -> str:
    return SYNONYM_LOOKUP[_cf(a, cf)].NAME

def syn_to_aliases(a: str, cf: bool = True) -> frozenset[str]:
    return SYNONYM_LOOKUP[_cf(a, cf)].ALIAS


def to_classes(attrs: Iterable[str], cf: bool = True) -> tuple[type[Attr], ...]:
    return tuple(syn_to_cls(attr, cf) for attr in attrs)

def to_instances(attrs: Iterable[str], values: Iterable[str], cf: bool = True) -> tuple[Attr, ...]:
    return tuple(cls(val) for cls, val in zip(to_classes(attrs, cf), values, strict=True))




def _init_module(highest_metaclass: type[Attr] = Attr):
    # Init classes and their data
    def identifier(typ: type):
        return typ.__name__
    
    global _init_module_done
    if _init_module_done:
        return
    
    CLASS_INIT_ARGS: dict[str, Iterable[Any]] = {}
    CLASS_INIT_KWARGS: dict[str, Mapping[str, Any]] = {}

    location_args = CLASS_INIT_ARGS[identifier(Location)] = [
        Location('Mushroom Kingdom', frozenset(["Mushroom"]), tags=frozenset([Location.Tag.KINGDOM])),
        Location('Cap Kingdom',      frozenset(["Cap"]),      tags=frozenset([Location.Tag.KINGDOM])),
        Location('Cascade Kingdom',  frozenset(["Cascade"]),  tags=frozenset([Location.Tag.KINGDOM])),
        Location('Sand Kingdom',     frozenset(["Sand"]),     tags=frozenset([Location.Tag.KINGDOM])),
        Location('Lake Kingdom',     frozenset(["Lake"]),     tags=frozenset([Location.Tag.KINGDOM])),
        Location('Wooded Kingdom',   frozenset(["Wooded"]),   tags=frozenset([Location.Tag.KINGDOM])),
        Location('Cloud Kingdom',    frozenset(["Cloud"]),    tags=frozenset([Location.Tag.KINGDOM])),
        Location('Lost Kingdom',     frozenset(["Lost"]),     tags=frozenset([Location.Tag.KINGDOM])),
        Location('Metro Kingdom',    frozenset(["Metro"]),    tags=frozenset([Location.Tag.KINGDOM])),
        Location('Snow Kingdom',     frozenset(["Snow"]),     tags=frozenset([Location.Tag.KINGDOM])),
        Location('Seaside Kingdom',  frozenset(["Seaside"]),  tags=frozenset([Location.Tag.KINGDOM])),
        Location('Luncheon Kingdom', frozenset(["Luncheon"]), tags=frozenset([Location.Tag.KINGDOM])),
        Location('Ruined Kingdom',   frozenset(["Ruined"]),   tags=frozenset([Location.Tag.KINGDOM])),
        Location("Bowser's Kingdom", frozenset(["Bowser's", "Bowser", "Bowsers", "Bowser Kingdom", "Bowsers Kingdom"]), tags=frozenset([Location.Tag.KINGDOM])),
        Location('Moon Kingdom',     frozenset(["Moon"]),     tags=frozenset([Location.Tag.KINGDOM])),
        Location('Dark Side',        frozenset(["Dark"]),     tags=frozenset([Location.Tag.KINGDOM])),
        Location('Darker Side',      frozenset(["Darker"]),   tags=frozenset([Location.Tag.KINGDOM]))
    ]
    location_args.append(Location(
        'Odyssey',
        inside=frozenset([*(loc for loc in location_args])),
        tags=frozenset([Location.Tag.MULTIPLE_KINGDOMS]))
    )
    location_args.append(Location(None))

    tier_args = CLASS_INIT_ARGS[identifier(Tier)] = [
        Tier('Practice Tier',  frozenset(["P", "Practice"])),
        Tier('Beginner',       frozenset(["B"])),
        Tier('Intermediate',   frozenset(["Int"])),
        Tier('Advanced',       frozenset(["A"])),
        Tier('Expert',         frozenset(["E"])),
        Tier('Master',         frozenset(["M"])),
        Tier('Low Elite',      frozenset(["L", "Low"])),
        Tier('Mid Elite',      frozenset(["M", "Mid"])),
        Tier('High Elite',     frozenset(["Hi", "High"])),
        Tier('Insanity Elite', frozenset(["I", "Ins", "Insanity"])),
        Tier('God Tier',       frozenset(["G", "God"])),
        Tier('Hell Tier',      frozenset(["He", "Hell"])),
        Tier('Unproven',       frozenset(["U"]))
    ]
    tier_args.append(Tier(None))
    
    difficulty_args = CLASS_INIT_ARGS[identifier(Difficulty)] = [
        Difficulty('0/10',           frozenset(['0']),         tier=tier_args[0]), 
        Difficulty('0.5/10',         frozenset(['0.5', '.5']), tier=tier_args[1]), 
        Difficulty('1/10',           frozenset(['1']),         tier=tier_args[1]), 
        Difficulty('1.5/10',         frozenset(['1.5']),       tier=tier_args[1]), 
        Difficulty('2/10',           frozenset(['2']),         tier=tier_args[1]), 
        Difficulty('2.5/10',         frozenset(['2.5']),       tier=tier_args[1]), 
        Difficulty('3/10',           frozenset(['3']),         tier=tier_args[1]), 
        Difficulty('3.5/10',         frozenset(['3.5']),       tier=tier_args[2]), 
        Difficulty('4/10',           frozenset(['4']),         tier=tier_args[2]), 
        Difficulty('4.5/10',         frozenset(['4.5']),       tier=tier_args[2]), 
        Difficulty('5/10',           frozenset(['5']),         tier=tier_args[2]), 
        Difficulty('5.5/10',         frozenset(['5.5']),       tier=tier_args[3]), 
        Difficulty('6/10',           frozenset(['6']),         tier=tier_args[3]), 
        Difficulty('6.5/10',         frozenset(['6.5']),       tier=tier_args[3]), 
        Difficulty('7/10',           frozenset(['7']),         tier=tier_args[4]), 
        Difficulty('7.5/10',         frozenset(['7.5']),       tier=tier_args[4]), 
        Difficulty('8/10',           frozenset(['8']),         tier=tier_args[4]), 
        Difficulty('8.5/10',         frozenset(['8.5']),       tier=tier_args[5]), 
        Difficulty('9/10',           frozenset(['9']),         tier=tier_args[5]), 
        Difficulty('9.5/10',         frozenset(['9.5']),       tier=tier_args[5]), 
        Difficulty('10/10',          frozenset(['10']),        tier=tier_args[5]),
        Difficulty('Low Elite',      frozenset(['Low']),       tier=tier_args[6]),  #dont mind me just watching  <- My boyfriend also wrote this
        Difficulty('Mid Elite',      frozenset(['Mid']),       tier=tier_args[7]), 
        Difficulty('High Elite',     frozenset(['High']),      tier=tier_args[8]), 
        Difficulty('Insanity Elite', frozenset(['Insanity']),  tier=tier_args[9]),
        Difficulty('God Tier',       frozenset(['God']),       tier=tier_args[10]), 
        Difficulty('Hell Tier',      frozenset(['Hell']),      tier=tier_args[11]), 
        Difficulty('Unproven',       frozenset(),            tier=tier_args[12], is_missing=False)
    ]
    difficulty_args.append(Difficulty(None, tier=tier_args[-1], is_missing=False))

    server_args = CLASS_INIT_ARGS[identifier(Server)] = [
        Server("Main Trickjumping Server", frozenset(["M", "Main", "Main Server", "Main Trickjump Server"])),
        Server("Database", frozenset(["D", "DB", "Database Server", "DB Server"]))
    ]
    server_args.append(Server(None))

    def init_recursively(cls: type[Attr]):
        for subclass in cls.__subclasses__():
            subclass._init_cls(
                *CLASS_INIT_ARGS.get(identifier(subclass), ()),
                **CLASS_INIT_KWARGS.get(identifier(subclass), {})
            )

            if subclass.__class__ not in (AttrCollection.__class__, AttrMultiValueCollectionBase.__class__) and issubclass(subclass, AttrCollection):
                assert subclass.ALL_INSTANCES, f"{subclass}"

            init_recursively(subclass)

    init_recursively(highest_metaclass)

    for key, cls in ATTR_ITEMS:
        cls.NAME = key

        for syn in (key, *cls.ALIAS):
            SYNONYM_LOOKUP[syn] = cls

_init_module()


# all in all good codi but want to play bsso uwuwuwuwuwuwuwuuwuwuwuuwuwuwuuwuwuwuwuwuwuwuw
# Thank you for the review my bf  - Joni