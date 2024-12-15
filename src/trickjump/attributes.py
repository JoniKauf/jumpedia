from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum, StrEnum, auto
from functools import cached_property
import functools
import inspect
from database import queries
from utils import text
import sys
from typing import Annotated, Any, Callable, ClassVar, Generic, Hashable, Iterable, Literal, Mapping, NamedTuple, Optional, Protocol, Self, Sequence, TypeAlias, TypeGuard, TypeVar, TypedDict, Union, TYPE_CHECKING, cast, final, get_args
import re
from collections.abc import KeysView, ValuesView, ItemsView

import discordtools.feedbackerrors as fbe
from users.person import Person
from utils.better_inbuilts import BetterSet




_init_module_done = False

@dataclass(frozen=True)
class AttrMetadata:
    accessible: bool


# --- Base Classes ---

class AttrAny[T](ABC):
    """An abstract base class for anything that represents an attribute.
    
    Metadata Class Variables:
    - NAME:
        The official key to map to the class, which should always be the
        class name in lower and snake case.
    - ALIAS:
        The aliases that act as alternatives to NAME as a mapping. Any 
        name or alias mapping to the same class is called a "syn" 
        (synonym) in the code.
    - REQUIRED:
        If not explicitly ignored, the attribute is required to  have a 
        value that is not falsy (empty, None, ...) for the context of an
        AttrComboClass.
    - MULTIVALUE:
        Defines if the attribute comes wrapped in an AttrMultiValue with
        possibly other instances of the same class for the context of an
        AttributeComboClass or if it just comes as a standalone.
    - USER_SPECIFIC:
        Defines if the attribute is about user-specific data.
    - SECRET:
        Defines if the attribute should not be shown to users.
    """

    def __init__(self) -> None:
        frame = inspect.currentframe()

        if frame is not None:
            caller = frame.f_back

            if caller is not None:
                cls: Optional[type[AttrAny]] = caller.f_locals.get("cls", None)
                self_: Optional[AttrAny] = caller.f_locals.get("self", None)

                if (cls is None or not issubclass(cls, AttrAny)) and (self_ is None or not isinstance(self, AttrAny)):
                    raise RuntimeError(
                        "Use the classmethod get(...) to create instances!"
                    )
                
        super().__init__()

    @classmethod
    def _init_cls(cls):
        """
        Initialize the class itself when the module is imported and 
        therefore runned the first time.
        """
        cls.NAME = text.pascal_to_snake(cls.__name__)

        if _init_module_done:
            raise RuntimeError(
                "Classes may only be initialized before themodule is fully "
                "initialized!"
            )
    
    @classmethod
    @abstractmethod
    def get(cls, value: Self | T | None, *args: Any, **kwargs: Any) -> Self:
        """Get an appropriate instance of a the specific class."""
        ...

    @property
    @abstractmethod
    def value(self) -> Optional[T]:
        """The value the class encapsulates."""

    @cached_property
    @abstractmethod
    def value_cls(self) -> type['AttrSingleValue']:
        """The class encapsulating the AttrSingleValue.
        
        For AttrSingleValue this is simply its own type, whereas for
        AttrMultiValue it's the type of the elements it contains. 
        
        This is especially useful if we have to deal with the
        possibility that an object could be an instance of either and
        we want to retrieve the AttrSingleValue's class.
        """

    @cached_property
    @abstractmethod
    def unpacked(self) -> tuple[Any, ...]:
        """The value(s) unpacked into a tuple.
        
        For AttrSingleValue this is simply a tuple of zero or one,
        depending on if the value of the class is None or not
        respectively. AttrMultiValue's value is a tuple of
        AttrSingleValue, this will "unpack" every value from each
        AttrSingleValue into a combined, new tuple.

        This is especially useful if we have to deal with the
        possibility that an object could be an instance of either and
        we want to retrieve a tuple of all elements' values, for example
        when iterating over them.
        """

    @cached_property
    @abstractmethod
    def packed(self) -> 'AttrMultiValue[AttrSingleValue]':
        """The AttrSingleValue(s) packed into a AttrMultiValue.
        
        For AttrMultiValue this is simply its own value, whereas for
        AttrSingleValue it's itself wrapped into an AttrMultiValue,
        which will either have a zero or one elements, depending on
        if the AttrSingleValue's value is None or not respectively.

        This is especially useful if we have to deal with the
        possibility that an object could be an instance of either and
        we want to retrieve a tuple of all elements, for example when 
        iterating over them.
        """
        ...

    @abstractmethod
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> Any:
        """Return an appropriate comparison value to be compared to
        other instances of the same type for sorting.
        
        Depending on the type of the value it should return a good value
        to be compared to others of the same type, such that sorting
        by the specific attribute follows a natural order. The sign
        acts as a way of reversing the order.
        """

type AttrAnyTypeT[VT] = (
    type[AttrSingleValue[VT]] | type[AttrMultiValue[AttrSingleValue[VT]]]
)
type AttrAnyT[VT] = AttrSingleValue[VT] | AttrMultiValue[AttrSingleValue[VT]]


class AttrSingleValue[VT](AttrAny[VT]):
    NAME: str
    ALIAS: frozenset[str]
    REQUIRED: bool
    MULTI_VALUE: bool
    USER_SPECIFIC: Optional[bool]
    SECRET: bool

    def __str__(self) -> str:
        return str(self.value)
    
    def __init__(self, value: Optional[VT]):
        self._value: Optional[VT] = value
        super().__init__()

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
    
    @cached_property
    def value(self) -> Optional[VT]:
        return self._value
    
    @cached_property
    def value_cls(self) -> type[Self]:
        return self.__class__

    @cached_property
    def unpacked(self) -> tuple[VT] | tuple[()]:
        return () if self.value is None else (self.value,)
    
    @cached_property
    def packed(self) -> 'AttrMultiValue[Self]':
        return AttrMultiValue.get(None if self.value is None else self, self.value_cls)

    @classmethod
    @abstractmethod
    def get(cls, value: Self | VT | None, *args: Any, **kwargs: Any) -> Self:
        ...
        
    
class AttrStr(AttrSingleValue[str]):
    def __init__(self, value: Optional[str]):
        if self.value and not self.value.strip():
            super().__init__(None)
        else:
            super().__init__(value)
    
    @classmethod
    def get(cls, value: Self | str | None, *args: Any, **kwargs: Any) -> Self:
        if value is None or isinstance(value, str):
            return cls(value)
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))
    
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> tuple[int, ...]:
        if self.value is None: 
            return (((sys.maxunicode + 1) * sign),)
        return tuple(ord(char) * sign for char in self.value.casefold())


class AttrStrEntry(AttrSingleValue[str]):
    LOOKUP: dict[str | int | None, Self] = {}

    def __init__(self, value: str | None, *, id: int, alias: frozenset[str] = frozenset()) -> None:
        if _init_module_done:
            raise RuntimeError(
                "No more objects of any collection can be created "
                "after the initialization of the module!"
            )
        
        self.id: int = id
        self.alias: Annotated[frozenset[str], AttrMetadata(True)] = alias

        super().__init__(value)
    
    @classmethod
    def _init_cls(cls) -> None:
        cls.LOOKUP[None] = cls(None, id=-1)
        return super()._init_cls()
    
    @classmethod
    def get(cls, value: Self | str | None, *args: Any, **kwargs: Any) -> Self:
        if value is None or isinstance(value, str):
            return cls.LOOKUP[value]
        if isinstance(value, cls):
            return value

        raise TypeError("Unexpected type:", type(value))

    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> int:
        return self.id * sign


class AttrDatetime(AttrSingleValue[datetime]):
    @classmethod
    def get(cls, value: Self | datetime | None, *args: Any, **kwargs: Any) -> Self:
        if value is None or isinstance(value, datetime):
            return cls(value)
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))
    
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> float:
        return (float("inf") if self.value is None else self.value.timestamp()) * sign


class AttrPerson(AttrSingleValue[Person]):
    ACTION: str

    @classmethod
    def get(cls, value: Self | Person | str | int | None, *args: Any, **kwargs: Any) -> Self:
        if value is None or isinstance(value, Person):
            return cls(value)
        if isinstance(value, (int, str)):
            try:
                return cls(Person.LOOKUP[value])
            except KeyError:
                raise fbe.PersonDoesNotExist(value)
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))
    
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> tuple[int, ...]:
        return AttrStr.sort_key(AttrStr(self.value.value if self.value is not None else self.value), sign=sign, **kwargs)
    

class AttrMultiValue[CT: AttrSingleValue](tuple[CT, ...], AttrAny[tuple[CT, ...]]):
    """
    A collection of multiple instances of the same Attr.
    An empty collection is converted to None and all None
    entries are also removed on initialization.
    """
    @property
    def value(self) -> tuple[CT, ...]:
        return tuple(self)
    
    @classmethod
    def __new__(cls, value: Optional[Iterable[CT]], value_cls: type[CT]) -> Self:
        value = value or ()
        if not all(value_cls == type(elem) for elem in value):
            raise TypeError("value_cls should be the exact same as the type of all elements of value")
        
        return super().__new__(cls, value)

    def __init__(self, value: Optional[Iterable[CT]], value_cls: type[CT]) -> None:
        self.value_cls: type[CT] = value_cls
        super().__init__()
    
    @cached_property
    def unpacked(self) -> tuple[Any, ...]:
        return tuple(elem.value for elem in self)
    
    @cached_property
    def packed(self) -> 'AttrMultiValue[CT]':
        return self
    
    def sort_key(self, sign: Literal[-1] | Literal[1] = +1, *args: Any, **kwargs: Any) -> tuple:
        if not self:
            return (self.value_cls.get(None).sort_key(sign),) * 2
        return tuple(elem.sort_key(sign) for elem in self)
    
    @classmethod
    def get(cls, value: Self | Iterable[CT | Any] | CT | Any | None, value_cls: type[CT], *args: Any, **kwargs: Any) -> Self:
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
    USER_SPECIFIC = None
    SECRET = False


class Location(AttrStrEntry):
    LOOKUP: dict[str | int | None, "Location"] = {}
    
    ALIAS: frozenset[str] = frozenset(["l", "loc", "k", "kd", "kingdom"])
    REQUIRED = True
    MULTI_VALUE = True
    USER_SPECIFIC = False
    SECRET = False

    def __init__(
        self, 
        value: Optional[str], 
        *, 
        id: int, 
        alias: frozenset[str] = frozenset(), 
        tag: frozenset[str] = frozenset(), 
        outer: frozenset[Self] = frozenset()
    ):
        self.outer: Annotated[frozenset[Self], AttrMetadata(True)] = outer
        self.tag: Annotated[frozenset[str], AttrMetadata(True)] = tag
        super().__init__(value, id=id, alias=alias)

    @classmethod
    def _init_cls(cls) -> None:
        with queries.connected() as (connection, cursor):
            cursor.execute(f"""
                SELECT 
                    location.id AS id,
                    location.name AS name,
                    location_alias.alias AS alias,
                    location_outer_junction.outer_id AS outer_id,
                    location_tag.tag AS tag
                FROM location
                LEFT JOIN location_alias ON location.id = location_alias.location_id
                LEFT JOIN location_outer_junction ON location.id = location_outer_junction.location_id
                LEFT JOIN location_tag_junction ON location.id = location_tag_junction.location_id
                LEFT JOIN location_tag ON location_tag_junction.tag_id = location_tag.id;
            """)

            rows: list = cursor.fetchall()

        result: dict[int, dict[str, BetterSet[Any]]] = queries.collapse_rows(rows, "id", collapsed_column_in_data=True)

        for location in result.values():
            id: int = location["id"].at(0)
            name: str = location["name"].at(0)

            cls.LOOKUP[id] = cls.LOOKUP[name] = Location(
                name,
                id=id,
                alias=location["alias"].freeze(),
                tag=location["tag"].freeze(),
                outer=frozenset(cls.LOOKUP[outer_id] for outer_id in location["outer_id"])
            )

        for location in cls.LOOKUP.values():
            print(location)
        return super()._init_cls()
    

class Tier(AttrStrEntry):
    LOOKUP: dict[str | int | None, "Tier"] = {}

    ALIAS: frozenset[str] = frozenset(["t"])
    REQUIRED = True
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = False


class Difficulty(AttrStrEntry):
    LOOKUP: dict[str | int | None, "Difficulty"] = {}

    ALIAS: frozenset[str] = frozenset(["diff", "d"])
    REQUIRED = True
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = False

    def __init__(self, value: Optional[str], *, tier: Optional[Tier] = None, id: int, is_missing: bool = True, alias: frozenset[str] = frozenset()):
        self.tier: Annotated[Tier, AttrMetadata(True)] = Tier.get(tier)
        self.is_missing: bool = is_missing
        super().__init__(value, id=id, alias=alias)


class Type(AttrStrEntry):
    LOOKUP: dict[str | int | None, "Type"] = {}

    ALIAS: frozenset[str] = frozenset(["t", "ty", "typ"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_SPECIFIC = False
    SECRET = False


class Server(AttrStrEntry):
    LOOKUP: dict[str | int | None, "Server"] = {}

    ALIAS: frozenset[str] = frozenset(["s", "serv"])
    REQUIRED = True
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = False


class Finder(AttrPerson):
    ACTION = "Found"

    ALIAS: frozenset[str] = frozenset(["f", "founder", "find", "found"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_SPECIFIC = False
    SECRET = False


class Taser(AttrPerson):
    ACTION = "TASed"

    ALIAS: frozenset[str] = frozenset(["tas", "tased"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_SPECIFIC = False
    SECRET = False


class Prover(AttrPerson):
    ACTION = "Proven"

    ALIAS: frozenset[str] = frozenset(["p", "prov", "proven"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_SPECIFIC = False
    SECRET = False


class FoundAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["fa", "f_a", "f_at"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = False


class TasedAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ta", "t_a", "t_at", "tas_at"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = False


class ProvenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["pa", "p_a", "p_at", "prov_at"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = False


class GivenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ga", "g_a", "g_at", "gave_at"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_SPECIFIC = True
    SECRET = False


class Proof(AttrStr):
    ALIAS: frozenset[str] = frozenset(["prof", "prove", "proven"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_SPECIFIC = True
    SECRET = False


class Link(AttrStr):
    ALIAS: frozenset[str] = frozenset(["l", "lnk", "clip", "video", "links"])
    REQUIRED = True
    MULTI_VALUE = True
    USER_SPECIFIC = False
    SECRET = False

    def __init__(self, value: Optional[str], *, author: Person):
        self.author: Annotated[Person, AttrMetadata(True)] = author
        super().__init__(value)


class Info(AttrStr):
    ALIAS: frozenset[str] = frozenset(["ex", "e", "extra", "i", "desc", "description", "data"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = False

    def __init__(self, value: Optional[str]):
        if value is not None:
            value = value.replace("\\n", "\n")

        super().__init__(value)

class Tag(AttrStrEntry):
    LOOKUP: dict[str | int | None, "Tag"] = {}

    ALIAS: frozenset[str] = frozenset(["tags"])
    REQUIRED = False
    MULTI_VALUE = True
    USER_SPECIFIC = False
    SECRET = False

class Thumbnail(AttrStr):
    ALIAS: frozenset[str] = frozenset(["tn", "thumb", "t_n", "th", "tnail"])
    REQUIRED = False
    MULTI_VALUE = False
    USER_SPECIFIC = False
    SECRET = True


@dataclass(init=False, slots=True)
class AttributeCollection:
    """
    A parent class for any class that wants to use attributes
    as its fields and provides functionality for that case.
    """
    __annotations__: ClassVar[dict[str, type[AttrAnyT]]]

    def __init__(self, data: dict[str, Any], *, required: bool = True, lower: bool = True) -> None:
        new_data: dict[str, AttrAnyT] = {}

        for k, v in data.items():
            try:
                cls = syn_to_cls(k, lower=lower)

                if cls not in self.field_types:
                    raise KeyError()
            except KeyError:
                raise fbe.InvalidAttribute(k)
            
            if cls.NAME in new_data:
                raise fbe.SameAttribute(k)

            new_data[cls.NAME] = AttrMultiValue.get(v, cls)
        
        missing: list[str] = []

        for cls in self.field_types:
            if cls.NAME not in new_data:
                new_data[cls.NAME] = cls.get(None)

                if required and cls.REQUIRED:
                    missing.append(cls.NAME)

        if missing:
            raise fbe.RequiredAttributesMissing(missing)

    @cached_property
    def field_types(self) -> dict[type[AttrSingleValue], None]:
        """dict instead of set because of insertion order"""
        return dict.fromkeys(
            elem.value_cls if isinstance(elem, AttrMultiValue) else elem.__class__ 
            for elem in self.values()
        )
    
    def mapping(self, predicate: Optional[Callable[[AttrAnyT], bool]] = None) -> dict[str, AttrAnyT]:
        if predicate is None:
            return asdict(self)
        return {k: v for k, v in asdict(self).items() if predicate(v)}
    
    @functools.cache
    def keys(self, predicate: Optional[Callable[[AttrAnyT], bool]] = None) -> KeysView[str]:
        return self.mapping(predicate).keys()
    
    def values(self, predicate: Optional[Callable[[AttrAnyT], bool]] = None) -> ValuesView[AttrAnyT]:
        return self.mapping(predicate).values()
    
    def items(self, predicate: Optional[Callable[[AttrAnyT], bool]] = None) -> ItemsView[str, AttrAnyT]:
        return self.mapping(predicate).items()

    def get(self, attr: str | type[AttrSingleValue]) -> AttrAnyT:
        if isinstance(attr, str):
            name: str = attr
        else:
            name: str = attr.NAME
        return getattr(self, name)

    def set(self, attr: str | type[AttrSingleValue], value: Any) -> AttrAnyT:
        if isinstance(attr, str):
            cls = syn_to_cls(attr)
        else:
            cls = attr
        
        name: str = cls.NAME
        instance: AttrSingleValue = cls.get(value)

        result: AttrAnyT = AttrMultiValue.get(instance, cls) if cls.MULTI_VALUE else instance

        setattr(self, name, result)
        return result

    def pop(self, attr: str | type[AttrSingleValue]) -> AttrAnyT:
        value: AttrAnyT = self.get(attr)
        setattr(self, value.NAME, value.__class__.get(None, value.value_cls))
        return value
    
    def get_value_for_user(self, expression: str) -> Any:
        parts: list[str] = [stripped for part in expression.split(".") if (stripped := part)]
        
        for i, part in enumerate(parts):
            # try converting attrs from syn to name
            try:
                parts[i] = syn_to_name(part, True)
            except KeyError:
                part = part.casefold()

        curr_obj: Any = self
        # expression = ".".join(parts)

        for i, part in enumerate(parts):
            is_valid: bool = False

            try:
                # possibly raises AttributeError or KeyError if no
                # annotation for the attr (which hold the metadata info)
                annotation = curr_obj.__annotations__[part]
                
                # possibly raises AttributeError if no metadata given
                for metadata in annotation.__metadata__:
                    if isinstance(metadata, AttrMetadata):
                        is_valid = metadata.accessible
                        break
                
                # possibly raises AttributeError if not tagged as 
                # accessible
                if not is_valid:
                    raise AttributeError()
                
                # possibly raises AttributeError if exists in
                # annotations but not as field anymore
                curr_obj = getattr(curr_obj, part)
            except (AttributeError, KeyError):
                if i == 0:
                    raise fbe.InvalidAttribute(part, expression=expression)
                else:
                    raise fbe.InvalidSubattribute(parts[i - 1], part, expression=expression)

        if isinstance(curr_obj, AttrAny):
            curr_obj = curr_obj.value

        return curr_obj
    

def _init_module():
    def recursively_iterate_subclasses[T](cls: type[T], do: Callable[[type[T]], None]):
        do(cls)

        for subclass in cls.__subclasses__():
            recursively_iterate_subclasses(subclass, do)

    recursively_iterate_subclasses(AttrSingleValue, lambda cls: cls._init_cls())

    def integrity_check_attribute_collection_subclasses(cls: type[AttributeCollection]):
        # TODO
        ...

    recursively_iterate_subclasses(AttributeCollection, integrity_check_attribute_collection_subclasses)

    global _init_module_done
    _init_module_done = True

_init_module()


ATTR_CLASSES = (Name, Location, Difficulty, Tier, Type, Finder, Taser, Prover, FoundAt, TasedAt, ProvenAt, GivenAt, Proof, Server, Tag, Link, Info, Thumbnail)
ATTR_NAMES = tuple(cls.NAME for cls in ATTR_CLASSES)
ATTR_ITEMS = tuple(zip(ATTR_NAMES, ATTR_CLASSES, strict=True))

NAME_TO_CLS_LOOKUP: dict[str, type[AttrSingleValue]] = {k: v for k, v in ATTR_ITEMS}
SYN_TO_CLS_LOOKUP: dict[str, type[AttrSingleValue]] = {syn: cls for cls in ATTR_CLASSES for syn in (cls.NAME, *cls.ALIAS)}

def _lower(a: str, lower: bool):
    return a.casefold() if lower else a


def is_name(a: str, lower: bool = True) -> bool:
    return _lower(a, lower) in NAME_TO_CLS_LOOKUP

def is_alias(a: str, lower: bool = True) -> bool:
    return _lower(a, lower) not in NAME_TO_CLS_LOOKUP and a in SYN_TO_CLS_LOOKUP

def is_syn(a: str, lower: bool = True) -> bool:
    return _lower(a, lower) in SYN_TO_CLS_LOOKUP

def name_to_cls(a: str, lower: bool = True) -> type[AttrSingleValue]:
    return NAME_TO_CLS_LOOKUP[_lower(a, lower)]

def syn_to_cls(a: str, lower: bool = True) -> type[AttrSingleValue]:
    return SYN_TO_CLS_LOOKUP[_lower(a, lower)]

def syn_to_name(a: str, lower: bool = True) -> str:
    return SYN_TO_CLS_LOOKUP[_lower(a, lower)].NAME

def syn_to_aliases(a: str, lower: bool = True) -> frozenset[str]:
    return SYN_TO_CLS_LOOKUP[_lower(a, lower)].ALIAS


# all in all good codi but want to play bsso uwuwuwuwuwuwuwuuwuwuwuuwuwuwuuwuwuwuwuwuwuwuw
# Thank you for the review my bf  - Joni