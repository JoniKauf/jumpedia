from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum, auto
from functools import cached_property
import functools
import json
import sys
from typing import Any, Callable, ClassVar, Generic, Hashable, Iterable, Literal, Mapping, NamedTuple, Optional, Protocol, Self, Sequence, TypeAlias, TypeGuard, TypeVar, TypedDict, Union, TYPE_CHECKING, cast, final, get_args
import re

from discordtools.errors import InvalidAttributeFeedbackError, PersonDoesNotExistFeedbackError, RequiredAttributesMissingFeedbackError, SameAttributeFeedbackError
from users.person import Person

if TYPE_CHECKING:
    from trickjump.trickjump import Trickjump


__init_module_done = False


_PASCAL_REPLACE_PATTERN = re.compile(r'[(?!^)([A-Z]+)]')

def pascal_to_snake(s: str):
    return re.sub(_PASCAL_REPLACE_PATTERN, r'_\1', s).lower()


# --- Meta Classes ---

class Attr[VT](ABC):
    @property
    @abstractmethod
    def value(self) -> VT:
        ...

    def __setattr__(self, name: str, value: Any) -> None:
        # if hasattr(self, "__init_done"):
        #     raise RuntimeError("Object cannot be modified after initialization")
        return super().__setattr__(name, value)
    
    @abstractmethod
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> Any:
        ...

    @classmethod
    def _init_cls(cls):
        pass

    NAME: str
    ALIAS: frozenset[str]
    REQUIRED: bool
    MULTI_VALUE: bool
    USER_ATTR: Optional[bool]
    SECRET: bool


class AttrSingleValue[VT](Attr[VT]):
    """
    Abstract base class for all attribute classes.
    An attribute class encapsulates data of a specific attribute,
    such that the attribute has more functionality, is easier to
    operate on and has its metadata is all stored in one place.
    """
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __init__(self, value: Optional[VT]):
        self.value: Optional[VT] = value
        super().__init__()

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
    
    @classmethod
    def _init_cls(cls):
        cls.NAME = pascal_to_snake(cls.__name__)

        if __init_module_done:
            raise RuntimeError("Classes may only be initialized before the module is fully initialized!")

    @classmethod
    @abstractmethod
    def get(cls, value: Self | VT | None) -> Self:
        ...


    
class AttrStr(AttrSingleValue[str]):
    """
    A attribute that specifically has str as its value and
    implements the functionalities associated.
    """

    def __init__(self, value: Optional[str]):
        if self.value and not self.value.strip():
            super().__init__(None)
        else:
            super().__init__(value)


    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> tuple[int, ...]:
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


class AttrStrEntry(AttrSingleValue[str]):
    LOOKUP: dict[str | int | None, Self] = {}

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
        cls.LOOKUP[None] = cls(None, id=-1)
        return super()._init_cls()
    
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> int:
        return self.id * sign
    
    @classmethod
    def get(cls, value: Self | str | None) -> Self:
        if value is None or isinstance(value, str):
            return cls.LOOKUP[value]
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))


class AttrDatetime(AttrSingleValue[datetime]):
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> float:
        return (float("inf") if self.value is None else self.value.timestamp()) * sign
    
    @classmethod
    def get(cls, value: Self | datetime | None) -> Self:
        if value is None or isinstance(value, datetime):
            return cls(value)
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))


class AttrPerson(AttrSingleValue[Person]):
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> tuple[int, ...]:
        return AttrStr.sort_key(AttrStr(self.value.value if self.value is not None else self.value), sign=sign, **kwargs)
    
    @classmethod
    def get(cls, value: Self | Person | str | int | None) -> Self:
        if value is None or isinstance(value, Person):
            return cls(value)
        if isinstance(value, (int, str)):
            try:
                return cls(Person.LOOKUP[value])
            except KeyError:
                raise PersonDoesNotExistFeedbackError(value)
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))
    

class AttrCollection[T: AttrSingleValue](tuple[T, ...], Attr[tuple[T, ...]]):
    """
    A collection of multiple instances of the same Attr.
    An empty collection is converted to None and all None
    entries are also removed on initialization.
    """
    @property
    def value(self) -> tuple[T, ...]:
        return tuple(self)
    
    @classmethod
    def __new__(cls, value: Optional[Iterable[T]], value_cls: type[T]) -> Self:
        value = value or ()
        if not all(value_cls == type(elem) for elem in value):
            raise TypeError("value_cls should be the exact same as the type of all elements of value")
        
        return super().__new__(cls, value)

    def __init__(self, value: Optional[Iterable[T]], value_cls: type[T]) -> None:
        self.value_cls: type[T] = value_cls
        super().__init__()
    
    @cached_property
    def unpacked(self) -> tuple[Any, ...]:
        return tuple(elem.value for elem in self)
    
    def sort_key(self, sign: Literal[-1] | Literal[1] = +1, *args: Any, **kwargs: Any) -> tuple:
        if not self:
            return (self.value_cls.get(None).sort_key(sign),) * 2
        return tuple(elem.sort_key(sign) for elem in self)
    
    @classmethod
    def get(cls, value: Self | Iterable[T | Any] | T | Any | None, value_cls: type[T]) -> Self:
        if value is None:
            return cls(value, value_cls)
        if isinstance(value, cls):
            return value
        if isinstance(value, Iterable):
            return cls(tuple(
                elem if isinstance(elem, value_cls) else value_cls(elem) for elem in value), 
                value_cls
            )
        return cls((value_cls.get(value),), value_cls)


# --- Attribute Classes ---

class Name(AttrStr):
    ALIAS: frozenset[str] = frozenset(["n"])
    REQUIRED = True
    MULTI_VALUE = False
    USER_ATTR = None
    SECRET = False


class Location(AttrStrEntry):
    def __init__(self, value: Optional[str], *, id: int, alias: frozenset[str] = frozenset(), tag: frozenset[str], outer: frozenset[Self]):
        self.outer: frozenset[Self] = outer
        self.tag: frozenset[str] = tag
        super().__init__(value, id=id, alias=alias)

    ALIAS: frozenset[str] = frozenset(["l", "loc", "k", "kd", "kingdom"])
    REQUIRED = True
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False
    

class Tier(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["t"])
    REQUIRED = True
    MULTI_VALUE = False
    USER_ATTR = False
    SECRET = False


class Difficulty(AttrStrEntry):
    def __init__(self, value: Optional[str], *, tier: Tier, id: int, is_missing: bool = True, alias: frozenset[str] = frozenset()):
        self.tier: Tier = tier
        self.is_missing: bool = is_missing
        super().__init__(value, id=id, alias=alias)

    ALIAS: frozenset[str] = frozenset(["diff", "d"])
    REQUIRED = True
    MULTI_VALUE = False
    USER_ATTR = False
    SECRET = False


class Type(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["t", "ty", "typ"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False


class Server(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["s", "serv"])
    REQUIRED = True
    MULTI_VALUE = False
    USER_ATTR = False
    SECRET = False


class Finder(AttrPerson):
    ALIAS: frozenset[str] = frozenset(["f", "founder", "find", "found"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False


class Taser(AttrPerson):
    ALIAS: frozenset[str] = frozenset(["tas", "tased"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False


class Prover(AttrPerson):
    ALIAS: frozenset[str] = frozenset(["p", "prov", "proven"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False


class FoundAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["fa", "f_a", "f_at"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_ATTR = False
    SECRET = False


class TasedAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ta", "t_a", "t_at", "tas_at"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_ATTR = False
    SECRET = False


class ProvenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["pa", "p_a", "p_at", "prov_at"])

    REQUIRED = False
    MULTI_VALUE = False
    USER_ATTR = False
    SECRET = False


class GivenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ga", "g_a", "g_at", "gave_at"])

    REQUIRED = False
    MULTI_VALUE = False
    USER_ATTR = True
    SECRET = False


class Proof(AttrStr):
    ALIAS: frozenset[str] = frozenset(["prof", "prove", "proven"])

    REQUIRED = False
    MULTI_VALUE = False
    USER_ATTR = True
    SECRET = False


class Link(AttrStr):
    def __init__(self, value: Optional[str], *, author: Person):
        self.author: Person = author
        super().__init__(value)
    
    ALIAS: frozenset[str] = frozenset(["l", "lnk", "clip", "video", "links"])
    REQUIRED = True
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False


class Info(AttrStr):
    ALIAS: frozenset[str] = frozenset(["ex", "e", "extra", "i", "desc", "description", "data"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False

class Tag(AttrStrEntry):
    ALIAS: frozenset[str] = frozenset(["tags"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_ATTR = False
    SECRET = False

class Thumbnail(AttrStr):
    ALIAS: frozenset[str] = frozenset(["tn", "thumb", "t_n", "th", "tnail"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_ATTR = False
    SECRET = True


def _init_module():
    def recursively_iterate_subclasses(cls: type[AttrSingleValue], do: Callable[[type[AttrSingleValue]], None]):
        do(cls)

        for subclass in cls.__subclasses__():
            recursively_iterate_subclasses(subclass, do)

    recursively_iterate_subclasses(AttrSingleValue, lambda cls: cls._init_cls())

    global __init_module_done
    __init_module_done = True

_init_module()


ATTR_CLASSES = (Name, Location, Difficulty, Tier, Type, Finder, Taser, Prover, FoundAt, TasedAt, ProvenAt, GivenAt, Proof, Server, Tag, Link, Info, Thumbnail)
ATTR_NAMES = tuple(cls.NAME for cls in ATTR_CLASSES)
ATTR_ITEMS = tuple(zip(ATTR_NAMES, ATTR_CLASSES, strict=True))

NAME_TO_CLS_LOOKUP: dict[str, type[AttrSingleValue]] = {k: v for k, v in ATTR_ITEMS}
SYN_TO_CLS_LOOKUP: dict[str, type[AttrSingleValue]] = {syn: cls for cls in ATTR_CLASSES for syn in (cls.NAME, *cls.ALIAS)}


class AttributeComboClass:
    """
    A parent class for any class that wants to use attributes
    as its ONLY fields and provides functionality for that case.
    """
    ATTRS_ORDERED: tuple[type[AttrSingleValue], ...] = ATTR_CLASSES
    ATTRS_MULTI_VALUE: set[type[AttrSingleValue]] = set(cls for cls in ATTR_CLASSES if cls.MULTI_VALUE)

    @classmethod
    @functools.cache
    def ATTRS_SET(cls) -> set[type[AttrSingleValue]]:
        return set(cls.ATTRS_ORDERED)

    def __init__(self, data: dict[str, Any], *, required: bool = True, cf: bool = True) -> None:
        new_data: dict[str, Attr] = {}

        for k, v in data.items():
            try:
                cls = syn_to_cls(k, cf=cf)

                if cls not in self.__class__.ATTRS_SET():
                    raise KeyError()
            except KeyError:
                raise InvalidAttributeFeedbackError(k)
            
            if cls.NAME in new_data:
                raise SameAttributeFeedbackError(k)
            
            if cls in self.__class__.ATTRS_MULTI_VALUE:
                result = AttrCollection[cls].get(v, cls) 
            else:
                result = cls.get(v)
            
            new_data[cls.NAME] = result
        
        missing: list[str] = []

        for cls in self.__class__.ATTRS_ORDERED:
            if cls.NAME not in new_data:
                new_data[cls.NAME] = cls.get(None)

                if required and cls.REQUIRED:
                    missing.append(cls.NAME)

        if missing:
            raise RequiredAttributesMissingFeedbackError(missing)
        
        self.__dict__: dict[str, Attr] = new_data


    def get(self, attr: type[AttrSingleValue] | AttrSingleValue | str) -> AttrSingleValue:
        if isinstance(attr, str):
            name = attr
        else:
            name = attr.NAME
        return getattr(self, name)

    def set(self, attr: type[AttrSingleValue] | AttrSingleValue | str, value: Any) -> None:
        if isinstance(attr, str):
            cls = syn_to_cls(attr)
            name = attr
        elif isinstance(attr, AttrSingleValue):
            cls = attr.__class__
            name = cls.NAME
        else:
            cls = attr
            name = cls.NAME

        setattr(self, name, cls(value))

    def pop(self, attr: type[AttrSingleValue] | AttrSingleValue | str) -> AttrSingleValue:
        attr = self.get(attr)
        setattr(self, attr.NAME, attr.__class__(None))
        return attr
    
    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self.__dict__, key=ATTR_NAMES.index))
    

def _cf(a: str, cf: bool):
    return a.casefold() if cf else a


def is_name(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in NAME_TO_CLS_LOOKUP

def is_alias(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) not in NAME_TO_CLS_LOOKUP and a in SYN_TO_CLS_LOOKUP

def is_syn(a: str, cf: bool = True) -> bool:
    return _cf(a, cf) in SYN_TO_CLS_LOOKUP

def name_to_cls(a: str, cf: bool = True) -> type[AttrSingleValue]:
    return NAME_TO_CLS_LOOKUP[_cf(a, cf)]

def syn_to_cls(a: str, cf: bool = True) -> type[AttrSingleValue]:
    return SYN_TO_CLS_LOOKUP[_cf(a, cf)]

def syn_to_name(a: str, cf: bool = True) -> str:
    return SYN_TO_CLS_LOOKUP[_cf(a, cf)].NAME

def syn_to_aliases(a: str, cf: bool = True) -> frozenset[str]:
    return SYN_TO_CLS_LOOKUP[_cf(a, cf)].ALIAS


# all in all good codi but want to play bsso uwuwuwuwuwuwuwuuwuwuwuuwuwuwuuwuwuwuwuwuwuwuw
# Thank you for the review my bf  - Joni