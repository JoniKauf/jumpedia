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

type JsonStrT = str

# --- Required Classes ---

class FS[T: Hashable](frozenset):
    def __new__(cls, *args: T) -> Self:
        return super(FS, cls).__new__(cls, args)
    

# --- Meta Classes ---
 
@dataclass(unsafe_hash=True)
class AttrBase[VT](ABC):
    """
    Abstract base class for all attribute classes.
    An attribute class encapsulates data of a specific attribute,
    such that the attribute has more functionality, is easier to
    operate on and has its metadata all stored in one place.
    """

    value: Optional[VT]
    
    NAME: ClassVar[str]
    ALIAS: ClassVar[FS[str]]

    REQUIRED: ClassVar[bool]
    USER_ATTR: ClassVar[bool | None]
    SECRET: ClassVar[bool]

    @classmethod
    def _init_cls(cls, *args, **kwargs):
        pass
    
    @abstractmethod
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> Any:
        ...

    def serialize(self) -> Optional[VT]:
        return self.value

    @classmethod
    def deserialize(cls, value: Optional[VT]) -> Self:
        return cls.get(value)

    @classmethod
    @abstractmethod
    def get(cls, value: Self | VT | None) -> Self:
        """Always use this method to create/lookup objects."""
        ...


@dataclass(unsafe_hash=True)
class MultiValue:
    value: Optional[tuple[AttrBase, ...]]
    unpacked: Optional[tuple[Any, ...]] = field(init=False) 
    
    def __post_init__(self):
        if not self.value:
            self.value = None
        
        self.unpacked = (
            None if self.value is None else
            tuple(elem.value for elem in self.value)
        )
            

@dataclass(unsafe_hash=True)
class Generate(ABC):

    @classmethod
    @abstractmethod
    def generate(cls, other_data: 'Attributes'):
        ...

    
@dataclass(unsafe_hash=True)
class AttrStrBase[VT = str](AttrBase[VT]):
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
class AttrMultiValueStrBase(MultiValue, AttrStrBase[tuple[AttrStrBase, ...]]):
    value: Optional[tuple[AttrStrBase, ...]]

    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> tuple[tuple[int, ...], ...]:
        # Sort None as very last element
        if self.value is None:
            return ((sys.maxunicode + 2,),)
        return tuple(elem.sort_key(sign) for elem in self.value)
    
    @classmethod
    def get(cls, value: Self | tuple[AttrStrBase | str | None, ...] | str | None) -> Self:
        if value is None:
            return cls(value)
        if isinstance(value, tuple):
            return cls(tuple(AttrStrBase.get(v) for v in value))
        if isinstance(value, str):
            return cls((AttrStrBase.get(value),))
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type: ", type(value))


@dataclass(unsafe_hash=True)
class AttrCollectionBase[VT: Hashable = str](AttrBase[VT]):
    alias: FS[str] = FS()
    
    ALL_INSTANCES: ClassVar[tuple[Self, ...]]
    GET: ClassVar[dict[Hashable, Self]]                          # All names and aliases mapped to their instances
    VALUES: ClassVar[dict[Hashable, int]]                        # All values mapped to their sorting value

    def __post_init__(self):
        if _init_module_done:
            raise RuntimeError(
                "No more objects of any collection attr can be created "
                "after the initialization of the module!"
            )
        
    @classmethod
    def _init_cls(cls, *all_instances: Self):
        cls.ALL_INSTANCES = all_instances
        cls.GET = {
            syn: self
            for self in all_instances
            for syn in (self.value, *self.alias)
        }
        cls.VALUES = {self.value: i for i, self in enumerate(all_instances)}
        

    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> int:
        return self.__class__.VALUES[self.value] * sign

    def serialize(self) -> Optional[VT]:
        return self.value
    
    @classmethod
    def deserialize(cls, value: Optional[VT]) -> Self:
        return cls.GET[value]
    
    @classmethod
    def get(cls, value: Self | str | None) -> Self:
        if value is None or isinstance(value, str):
            return cls.GET[value]
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type: ", type(value))


@dataclass(unsafe_hash=True)
class AttrMultiValueCollectionBase(MultiValue, AttrCollectionBase[tuple[AttrCollectionBase, ...]]):
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> tuple[int, ...]:
        if self.value is None:
            return (len(self.__class__.VALUES),) * sign
        return tuple(self.__class__.VALUES[elem.value] * sign for elem in self.value)
    
    def serialize(self) -> Optional[JsonStrT]:
        if self.value is None:
            return self.value
        return json.dumps(tuple(elem.value for elem in self.value))
    
    @classmethod
    def deserialize(cls, value: Optional[JsonStrT]) -> Self:
        return cls.get(value if value is None else json.loads(value))
    
    @classmethod
    def get(cls, value: Self | tuple[AttrCollectionBase | str | None, ...] | str | None) -> Self:
        if value is None:
            return cls(value)
        if isinstance(value, tuple):
            return cls(tuple(AttrCollectionBase.get(v) for v in value))
        if isinstance(value, str):
            return cls((AttrCollectionBase.get(value),))
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type: ", type(value))



@dataclass(unsafe_hash=True)
class AttrDatetimeBase(AttrBase[datetime]):
    def sort_key(self, sign: Literal[-1, +1] = +1, **kwargs: Any) -> float:
        return (float("inf") if self.value is None else self.value.timestamp()) * sign



# --- Attribute Classes ---

@dataclass(unsafe_hash=True)
class Name(AttrStrBase):
    ALIAS: ClassVar[FS[str]] = FS("n")

    REQUIRED = True
    USER_ATTR = None
    SECRET = False


@dataclass(unsafe_hash=True)
class Location(AttrCollectionBase):
    class Tag(Enum):
        KINGDOM = "Kingdom"
        MULTIPLE_KINGDOMS = "Multiple Kingdoms"
        
    inside: FS[Self] = FS()
    tags: FS[Tag] = FS()

    ALIAS: ClassVar[FS[str]] = FS("l", "loc", "k", "kd", "kingdom")

    REQUIRED = True
    USER_ATTR = False
    SECRET = False

    PathT = ClassVar[list[Union['Location', 'PathT']]]  # recursive

    def get_all_paths(self) -> PathT:
        def walk(loc: Self) -> Location.PathT:
            if not loc.inside:
                return [loc]
            else:
                paths = []
                for inner_loc in loc.inside:
                    for path in walk(inner_loc):
                        paths.append([loc] + (path if isinstance(path, list) else [path]))
                return paths
        
        return walk(self)


@dataclass(unsafe_hash=True, kw_only=True)
class Difficulty(AttrCollectionBase):
    tier: 'Tier'
    is_missing: bool = True

    ALIAS: ClassVar[FS[str]] = FS("diff", "d")

    REQUIRED = True
    USER_ATTR = False
    SECRET = False
    

@dataclass(unsafe_hash=True)
class Tier(Generate, AttrCollectionBase):
    ALIAS: ClassVar[FS[str]] = FS()

    REQUIRED = True
    USER_ATTR = False
    SECRET = False

    @classmethod
    def generate(cls, other_data: 'Attributes') -> 'Tier':
        return Tier.get(None) if other_data.difficulty is None else other_data.difficulty.tier 
    
    

@dataclass(unsafe_hash=True)
class Server(AttrCollectionBase):
    ALIAS: ClassVar[FS[str]] = FS("s", "serv")

    REQUIRED = True
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Type(AttrStrBase):
    # TODO:
    # - Collection
    # - required = True

    ALIAS: ClassVar[FS[str]] = FS("t", "ty", "typ")

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Finder(AttrMultiValueStrBase):
    ALIAS: ClassVar[FS[str]] = FS("f", "founder", "find", "found")

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Taser(AttrMultiValueStrBase):
    ALIAS: ClassVar[FS[str]] = FS("tas", "tased")
    
    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Prover(AttrMultiValueStrBase):
    ALIAS: ClassVar[FS[str]] = FS("p", "prov", "proven")

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class FoundAt(AttrDatetimeBase):
    ALIAS: ClassVar[FS[str]] = FS("fa", "f_a", "f_at")

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class TasedAt(AttrDatetimeBase):
    ALIAS: ClassVar[FS[str]] = FS("ta", "t_a", "t_at", "tas_at")

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class ProvenAt(AttrDatetimeBase):
    ALIAS: ClassVar[FS[str]] = FS("pa", "p_a", "p_at", "prov_at")

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class GivenAt(AttrDatetimeBase):
    ALIAS: ClassVar[FS[str]] = FS("ga", "g_a", "g_at", "gave_at")

    REQUIRED = False
    USER_ATTR = True
    SECRET = False


@dataclass(unsafe_hash=True)
class Proof(AttrStrBase):
    ALIAS: ClassVar[FS[str]] = FS("prof", "prove", "proven")

    REQUIRED = False
    USER_ATTR = True
    SECRET = False


@dataclass(unsafe_hash=True)
class Link(AttrMultiValueStrBase):
    ALIAS: ClassVar[FS[str]] = FS("l", "lnk", "clip", "video")

    REQUIRED = True
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Extra(AttrMultiValueStrBase):
    ALIAS: ClassVar[FS[str]] = FS("ex", "e", "info", "i", "desc", "description", "data")

    REQUIRED = False
    USER_ATTR = False
    SECRET = False


@dataclass(unsafe_hash=True)
class Thumbnail(AttrStrBase):
    ALIAS: ClassVar[FS[str]] = FS("tn", "thumb", "t_n", "th", "tnail")

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


    def get(self, attr: __type[AttrBase] | AttrBase | str) -> AttrBase:
        if isinstance(attr, str):
            name = attr
        else:
            name = attr.NAME
        return getattr(self, name)

    def set(self, attr: __type[AttrBase] | AttrBase | str, value: Any) -> None:
        if isinstance(attr, str):
            cls = syn_to_cls(attr)
            name = attr
        else:
            cls = attr.__class__
            name = cls.NAME

        setattr(self, name, cls(value))

    def pop(self, attr: __type[AttrBase] | AttrBase | str) -> AttrBase:
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


_ATTR_DCT: dict[str, type[AttrBase]] = {k: v for k, v in ATTR_ITEMS}

SYNONYM_LOOKUP: dict[str, type[AttrBase]] = {}  # fill out further down

def _cf(a: str, cf: bool):
    return a.casefold() if cf else a


def is_name(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in _ATTR_DCT

def is_alias(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) not in _ATTR_DCT and a in SYNONYM_LOOKUP

def is_syn(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in SYNONYM_LOOKUP

def syn_to_cls(a: str, cf: bool = True) -> type[AttrBase]:
    return SYNONYM_LOOKUP[_cf(a, cf)]

def syn_to_name(a: str, cf: bool = True) -> str:
    return SYNONYM_LOOKUP[_cf(a, cf)].NAME

def syn_to_aliases(a: str, cf: bool = True) -> FS[str]:
    return SYNONYM_LOOKUP[_cf(a, cf)].ALIAS


def to_classes(attrs: Iterable[str], cf: bool = True) -> tuple[type[AttrBase], ...]:
    return tuple(syn_to_cls(attr, cf) for attr in attrs)

def to_instances(attrs: Iterable[str], values: Iterable[str], cf: bool = True) -> tuple[AttrBase, ...]:
    return tuple(cls(val) for cls, val in zip(to_classes(attrs, cf), values, strict=True))




def _init_module(highest_metaclass: type[AttrBase] = AttrBase):
    # Init classes and their data
    def identifier(typ: type):
        return typ.__name__
    
    global _init_module_done
    if _init_module_done:
        return
    
    CLASS_INIT_ARGS: dict[str, Iterable[Any]] = {}
    CLASS_INIT_KWARGS: dict[str, Mapping[str, Any]] = {}

    location_args = CLASS_INIT_ARGS[identifier(Location)] = [
        Location('Mushroom Kingdom', FS("Mushroom"), tags=FS(Location.Tag.KINGDOM)),
        Location('Cap Kingdom',      FS("Cap"),      tags=FS(Location.Tag.KINGDOM)),
        Location('Cascade Kingdom',  FS("Cascade"),  tags=FS(Location.Tag.KINGDOM)),
        Location('Sand Kingdom',     FS("Sand"),     tags=FS(Location.Tag.KINGDOM)),
        Location('Lake Kingdom',     FS("Lake"),     tags=FS(Location.Tag.KINGDOM)),
        Location('Wooded Kingdom',   FS("Wooded"),   tags=FS(Location.Tag.KINGDOM)),
        Location('Cloud Kingdom',    FS("Cloud"),    tags=FS(Location.Tag.KINGDOM)),
        Location('Lost Kingdom',     FS("Lost"),     tags=FS(Location.Tag.KINGDOM)),
        Location('Metro Kingdom',    FS("Metro"),    tags=FS(Location.Tag.KINGDOM)),
        Location('Snow Kingdom',     FS("Snow"),     tags=FS(Location.Tag.KINGDOM)),
        Location('Seaside Kingdom',  FS("Seaside"),  tags=FS(Location.Tag.KINGDOM)),
        Location('Luncheon Kingdom', FS("Luncheon"), tags=FS(Location.Tag.KINGDOM)),
        Location('Ruined Kingdom',   FS("Ruined"),   tags=FS(Location.Tag.KINGDOM)),
        Location("Bowser's Kingdom", FS("Bowser's", "Bowser", "Bowsers", "Bowser Kingdom", "Bowsers Kingdom"), tags=FS(Location.Tag.KINGDOM)),
        Location('Moon Kingdom',     FS("Moon"),     tags=FS(Location.Tag.KINGDOM)),
        Location('Dark Side',        FS("Dark"),     tags=FS(Location.Tag.KINGDOM)),
        Location('Darker Side',      FS("Darker"),   tags=FS(Location.Tag.KINGDOM))
    ]
    location_args.append(Location(
        'Odyssey',
        inside=FS(*(loc for loc in location_args)),
        tags=FS(Location.Tag.MULTIPLE_KINGDOMS))
    )
    location_args.append(Location(None))

    tier_args = CLASS_INIT_ARGS[identifier(Tier)] = [
        Tier('Practice Tier',  FS("P", "Practice")),
        Tier('Beginner',       FS("B")),
        Tier('Intermediate',   FS("Int")),
        Tier('Advanced',       FS("A")),
        Tier('Expert',         FS("E")),
        Tier('Master',         FS("M")),
        Tier('Low Elite',      FS("L", "Low")),
        Tier('Mid Elite',      FS("M", "Mid")),
        Tier('High Elite',     FS("Hi", "High")),
        Tier('Insanity Elite', FS("I", "Ins", "Insanity")),
        Tier('God Tier',       FS("G", "God")),
        Tier('Hell Tier',      FS("He", "Hell")),
        Tier('Unproven',       FS("U"))
    ]
    tier_args.append(Tier(None))
    
    difficulty_args = CLASS_INIT_ARGS[identifier(Difficulty)] = [
        Difficulty('0/10',           FS('0'),         tier=tier_args[0]), 
        Difficulty('0.5/10',         FS('0.5', '.5'), tier=tier_args[1]), 
        Difficulty('1/10',           FS('1'),         tier=tier_args[1]), 
        Difficulty('1.5/10',         FS('1.5'),       tier=tier_args[1]), 
        Difficulty('2/10',           FS('2'),         tier=tier_args[1]), 
        Difficulty('2.5/10',         FS('2.5'),       tier=tier_args[1]), 
        Difficulty('3/10',           FS('3'),         tier=tier_args[1]), 
        Difficulty('3.5/10',         FS('3.5'),       tier=tier_args[2]), 
        Difficulty('4/10',           FS('4'),         tier=tier_args[2]), 
        Difficulty('4.5/10',         FS('4.5'),       tier=tier_args[2]), 
        Difficulty('5/10',           FS('5'),         tier=tier_args[2]), 
        Difficulty('5.5/10',         FS('5.5'),       tier=tier_args[3]), 
        Difficulty('6/10',           FS('6'),         tier=tier_args[3]), 
        Difficulty('6.5/10',         FS('6.5'),       tier=tier_args[3]), 
        Difficulty('7/10',           FS('7'),         tier=tier_args[4]), 
        Difficulty('7.5/10',         FS('7.5'),       tier=tier_args[4]), 
        Difficulty('8/10',           FS('8'),         tier=tier_args[4]), 
        Difficulty('8.5/10',         FS('8.5'),       tier=tier_args[5]), 
        Difficulty('9/10',           FS('9'),         tier=tier_args[5]), 
        Difficulty('9.5/10',         FS('9.5'),       tier=tier_args[5]), 
        Difficulty('10/10',          FS('10'),        tier=tier_args[5]),
        Difficulty('Low Elite',      FS('Low'),       tier=tier_args[6]),  #dont mind me just watching  <- My boyfriend also wrote this
        Difficulty('Mid Elite',      FS('Mid'),       tier=tier_args[7]), 
        Difficulty('High Elite',     FS('High'),      tier=tier_args[8]), 
        Difficulty('Insanity Elite', FS('Insanity'),  tier=tier_args[9]),
        Difficulty('God Tier',       FS('God'),       tier=tier_args[10]), 
        Difficulty('Hell Tier',      FS('Hell'),      tier=tier_args[11]), 
        Difficulty('Unproven',       FS(),            tier=tier_args[12], is_missing=False)
    ]
    difficulty_args.append(Difficulty(None, tier=tier_args[-1], is_missing=False))

    server_args = CLASS_INIT_ARGS[identifier(Server)] = [
        Server("Main Trickjumping Server", FS("M", "Main", "Main Server", "Main Trickjump Server")),
        Server("Database", FS("D", "DB", "Database Server", "DB Server"))
    ]
    server_args.append(Server(None))

    def init_recursively(cls: type[AttrBase]):
        for subclass in cls.__subclasses__():
            subclass._init_cls(
                *CLASS_INIT_ARGS.get(identifier(subclass), ()),
                **CLASS_INIT_KWARGS.get(identifier(subclass), {})
            )

            if subclass.__class__ not in (AttrCollectionBase.__class__, AttrMultiValueCollectionBase.__class__) and issubclass(subclass, AttrCollectionBase):
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