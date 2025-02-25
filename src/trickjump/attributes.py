from dataclasses import Field, asdict, dataclass, fields
from datetime import datetime
from functools import cached_property
import functools
import inspect
import typing
from utils import text
import sys
from typing import Any, Callable, ClassVar as CV, Iterable, Literal, Optional as Opt, Protocol, Self, get_args, get_origin, runtime_checkable
import re
from collections.abc import KeysView, ValuesView, ItemsView

import discordtools.feedbackerrors as fbe
from people.person import Person


_init_module_done = False

MAX_LINK_LENGTH = 512

# Recursive fix for https://bugs.python.org/issue44847
def _issubclass(cls: Any, parent: Any):
    if cls == parent:
        return True
    
    for base in getattr(cls, '__bases__', ()):
        return _issubclass(base, parent)
    
    return False

def fs[T](*elems: T) -> frozenset[T]:
    return frozenset(elems)


# --- Base Classes ---

@runtime_checkable
class AttrAny[T](Protocol):
    ACCESSIBLE: bool = True
    EDITABLE: bool = True

    @property
    def value(self) -> T:
        """The value the class encapsulates."""
        raise NotImplementedError()

    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.get({repr(self.value)})"


class AttrSub[T](AttrAny[T]):
    def __init__(self, value: T) -> None:
        self._value = value
        super().__init__()

    @property
    def value(self) -> T:
        return self._value
    

class SortValueSub(AttrSub[int]):
    ACCESSIBLE = False
    EDITABLE = True

class OuterSub(AttrSub[frozenset['Location']]):
    ACCESSIBLE = True
    EDITABLE = True

class TagSub(AttrSub[frozenset[str]]):
    ACCESSIBLE = True
    EDITABLE = True

class TierSub(AttrSub['Tier']):
    ACCESSIBLE = True
    EDITABLE = True

class AuthorSub(AttrSub[Opt[Person]]):
    ACCESSIBLE = True
    EDITABLE = True


    
class AttrNormal[T](AttrAny[Opt[T]]):
    """An abstract base class for anything that represents a "normal" attribute.
    
    Metadata Class Variables:
    - NAME:
        The official key to map to the class, which should always be the
        class name in lower and snake case.
    - ALIAS:
        The aliases that act as alternatives to NAME as a mapping. Any 
        name or alias mapping to the same class is called a "syn" 
        (synonym) in the code.
    - REQUIRED:
        If not explicitly ignored, the attribute is required to have a 
        value that is not falsy (empty, None, ...) for the context of an
        AttributeCollection.
    - MULTIVALUE:
        Defines if the attribute comes wrapped in an AttrMultiValue with
        possibly other instances of the same class for the context of an
        AttributeCollection or if it just comes as a standalone.
    - SECRET:
        Defines if the attribute should not be shown to users.
    """

    def __init__(self) -> None:
        frame = inspect.currentframe()

        if frame is not None:
            caller = frame.f_back

            if caller is not None:
                cls: Opt[type[AttrNormal]] = caller.f_locals.get("cls", None)
                self_: Opt[AttrNormal] = caller.f_locals.get("self", None)

                if (cls is None or not issubclass(cls, AttrNormal)) and (self_ is None or not isinstance(self, AttrNormal)):
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
        if _init_module_done:
            raise RuntimeError(
                "Classes may only be initialized before themodule is fully "
                "initialized!"
            )
    
    @classmethod
    def get(cls, value: Self | T | None, *args: Any, **kwargs: Any) -> Self:
        """Get an appropriate instance of the specific class."""
        raise NotImplementedError()

    @property
    def value(self) -> Opt[T]:
        raise NotImplementedError()
    
    @property
    def value_cls(self) -> type['AttrSingleValue']:
        """The class encapsulating the AttrSingleValue.
        
        For AttrSingleValue this is simply its own type, whereas for
        AttrMultiValue it's the type of the elements it contains. 
        
        This is especially useful if we have to deal with the
        possibility that an object could be an instance of either and
        we want to retrieve the AttrSingleValue's class.
        """
        raise NotImplementedError()

    @property
    def unpacked(self) -> tuple[Any, ...]:
        """The value(s) unpacked into a tuple.
        
        For AttrSingleValue this is simply a tuple of length zero or one,
        depending on if the value of the class is None or not,
        respectively. AttrMultiValue's value is a tuple of
        AttrSingleValue, this will "unpack" every value from each
        AttrSingleValue into a combined, new tuple.

        This is especially useful if we have to deal with the
        possibility that an object could be an instance of either and
        we want to retrieve a tuple of all elements' values, for example
        when iterating over them.
        """
        raise NotImplementedError()

    @property
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
        raise NotImplementedError()

    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> Any:
        """Return an appropriate comparison value to be compared to
        other instances of the same type for sorting.
        
        Depending on the type of the value it should return a good value
        to be compared to others of the same type, such that sorting
        by the specific attribute follows a natural order. The sign
        acts as a way of reversing the order.
        """
        raise NotImplementedError()

    def is_empty(self) -> bool:
        raise NotImplementedError()
    

type AttrNormalTypeT[VT] = (
    type[AttrSingleValue[VT]] | type[AttrMultiValue[AttrSingleValue[VT]]]
)
type AttrNormalT[VT] = (
    AttrSingleValue[VT] | AttrMultiValue[AttrSingleValue[VT]]
)
type AttrAnyTypeT[VT] = (
    AttrNormalTypeT[VT] | type[AttrSub[VT]]
)
type AttrAnyT[VT] = (
    AttrNormalT[VT] | AttrNormalT
)

class AttrSingleValue[VT](AttrNormal[VT]):
    NAME: str
    ALIAS: frozenset[str]
    REQUIRED: bool
    MULTI_VALUE: bool
    SECRET: bool
    
    def __init__(self, value: Opt[VT]):
        self._value: Opt[VT] = value
        super().__init__()

    @classmethod
    def _init_cls(cls):
        super()._init_cls()
        
        cls.NAME = text.pascal_to_snake(cls.__name__)
    
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
    
    @property
    def value(self) -> Opt[VT]:
        return self._value
    
    @property
    def value_cls(self) -> type[Self]:
        return self.__class__

    @cached_property
    def unpacked(self) -> tuple[VT] | tuple[()]:
        return () if self.value is None else (self.value,)
    
    @cached_property
    def packed(self) -> 'AttrMultiValue[Self]':
        return AttrMultiValue.get(None if self.value is None else self, self.value_cls)

    @classmethod
    def get(cls, value: Self | VT | None, *args: Any, **kwargs: Any) -> Self:
        raise NotImplementedError()
    
    def is_empty(self) -> bool:
        return self.value is None

class AttrInt(AttrSingleValue[int]):
    def __init__(self, value: Opt[int]):
        super().__init__(value)

    @classmethod
    def get(cls, value: Self | int | str | None, *args: Any, **kwargs: Any) -> Self:
        if value is None or isinstance(value, int):
            return cls(value)
        
        if isinstance(value, str):
            try:
                return cls(int(value))
            except ValueError:
                raise fbe.NotANumber(value)
            
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))
    
    def sort_key(self, sign: Literal[-1] | Literal[1] = +1, *args: Any, **kwargs: Any) -> Any:
        if self.value is None:
            return sys.maxsize * sign
        return self.value * sign
    
    
class AttrStr(AttrSingleValue[str]):
    MAX_LENGTH: CV[int]

    def __init__(self, value: Opt[str]):
        if value and not value.strip():
            super().__init__(None)
        else:
            super().__init__(value)
    
    @classmethod
    def get(cls, value: Self | str | None, *args: Any, **kwargs: Any) -> Self:
        if value is None or isinstance(value, str):
            if value is not None and len(value) > cls.MAX_LENGTH:
                raise fbe.TooLongValue(value, cls.MAX_LENGTH)
            return cls(value)
        
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))
    
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> tuple[int, ...]:
        if self.value is None: 
            return (((sys.maxunicode + 1) * sign),)
        return tuple(ord(char) * sign for char in self.value.casefold())


class AttrStrBundle(AttrSingleValue[str]):
    LOOKUP: dict[str | int | None, Self] = {}

    def __init__(self, value: str | None, *, id: int, sort_value: int, alias: frozenset[str] = frozenset()) -> None:
        if _init_module_done:
            raise RuntimeError(
                "No more objects of any collection can be created "
                "after the initialization of the module!"
            )
        
        self.id: int = id
        self.sort_value = sort_value
        self.alias = alias

        super().__init__(value)
    
    @classmethod
    def _add_raw_data(cls, *values: dict[str, Any]) -> None:
        already_added = len({elem.id for elem in cls.LOOKUP.values()})

        if None in cls.LOOKUP:
            already_added -= 1

        for i, elem in enumerate(values, start=already_added + 1):
            # add these kv only if not existant already
            elem: dict[str, Any] = {'id': i, 'sort_value': i} | elem
            
            obj = cls(**elem)
            
            for syn_or_id in (
                obj.id, 
                obj.value.casefold() if obj.value is not None else None, 
                *(alias.casefold() for alias in obj.alias)
            ):
                cls.LOOKUP[syn_or_id] = obj

    @classmethod
    def _init_cls(cls) -> None:
        super()._init_cls()

        # If we reach 2^32 - 1 elements, we definitely have other problems
        cls.LOOKUP[None] = cls(None, id=-1, sort_value=sys.maxsize - 1)
    
    @classmethod
    def get(cls, value: Self | str | int | None, *args: Any, **kwargs: Any) -> Self:
        if value is None or isinstance(value, int):
            return cls.LOOKUP[value]
        if isinstance(value, str):
            return cls.LOOKUP[value.casefold()]
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
            return cls(Person.get(value))
        if isinstance(value, cls):
            return value
        
        raise TypeError("Unexpected type:", type(value))
    
    def sort_key(self, sign: Literal[-1, +1] = +1, *args: Any, **kwargs: Any) -> tuple[int, ...]:
        return AttrStr.sort_key(AttrStr(self.value.value if self.value is not None else self.value), sign=sign, **kwargs)
    

class AttrMultiValue[CT: AttrSingleValue](tuple[CT, ...], AttrNormal[tuple[CT, ...]]):
    """
    A collection of multiple instances of the same Attr.
    An empty collection is converted to None and all None
    entries are also removed on initialization.
    """
    @property
    def value(self) -> tuple[CT, ...]:
        return tuple(self)
    
    def __new__(cls, value: Opt[Iterable[CT]], value_cls: type[CT]) -> Self:
        value = value or ()
        if not all(value_cls == type(elem) for elem in value):
            raise TypeError("value_cls should be the exact same as the type of all elements of value")
        
        return super().__new__(cls, value)

    def __init__(self, value: Opt[Iterable[CT]], value_cls: type[CT]) -> None:
        self._value_cls: type[CT] = value_cls
        super().__init__()
    
    def __str__(self) -> str:
        return str(tuple(str(elem) for elem in self.unpacked))
    
    @cached_property
    def unpacked(self) -> tuple[Any, ...]:
        return tuple(elem.value for elem in self)
    
    @property
    def packed(self) -> 'AttrMultiValue[CT]':
        return self
    
    @property
    def value_cls(self) -> type[CT]:
        return self._value_cls
    
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
            return cls(
                tuple(value_cls.get(elem) for elem in value), 
                value_cls
            )
        return cls([value_cls.get(value),], value_cls)
    
    def is_empty(self) -> bool:
        return self == ()


# --- Attribute Classes ---

class Id(AttrInt):
    ALIAS: frozenset[str] = frozenset()
    REQUIRED = True
    MULTI_VALUE = False
    SECRET = True

class Name(AttrStr):
    ALIAS: frozenset[str] = frozenset(["n"])
    REQUIRED = True
    MULTI_VALUE = False
    SECRET = False

    MAX_LENGTH = 80


class Location(AttrStrBundle):
    LOOKUP: dict[str | int | None, 'Location'] = {}
    
    ALIAS: frozenset[str] = frozenset(["l", "loc", "k", "kd", "kingdom"])
    REQUIRED = True
    MULTI_VALUE = True
    SECRET = False

    def __init__(
        self, 
        value: Opt[str], 
        *, 
        id: int, 
        sort_value: int,
        alias: frozenset[str] = frozenset(), 
        tag: frozenset[str] = frozenset(), 
        outer: frozenset['Location'] = frozenset()
    ):
        self.outer = OuterSub(outer)
        self.tag = TagSub(tag)
        super().__init__(value, id=id, sort_value=sort_value, alias=alias)

    @classmethod
    def _init_cls(cls) -> None:
        super()._init_cls()

        data: list[dict[str, Any]] = [
            {'value': "Cap Kingdom"},
            {'value': "Cascade Kingdom"},
            {'value': "Sand Kingdom"},
            {'value': "Lake Kingdom"},
            {'value': "Wooded Kingdom"},
            {'value': "Cloud Kingdom"},
            {'value': "Lost Kingdom"},
            {'value': "Metro Kingdom"},
            {'value': "Snow Kingdom"},
            {'value': "Seaside Kingdom"},
            {'value': "Luncheon Kingdom"},
            {'value': "Ruined Kingdom"},
            bowser := {'value': "Bowser's Kingdom"},
            {'value': "Moon Kingdom"},
            {'value': "Mushroom Kingdom"},
            {'value': "Dark Side"},
            {'value': "Darker Side"},
        ]
        
        for elem in data:
            elem |= {'alias': frozenset([elem['value'].partition(" ")[0]]), 'outer': frozenset()}

        bowser['alias'] |= frozenset(["Bowser", "Bowsers", "Bowser Kingdom", "Bowsers Kingdom"])

        cls._add_raw_data(*data)
        cls._add_raw_data(
            {'value': "Odyssey", 'outer': frozenset(elem for elem in cls.LOOKUP.values())}
        )
    

class Tier(AttrStrBundle):
    LOOKUP: dict[str | int | None, 'Tier'] = {}

    ALIAS: frozenset[str] = frozenset(['t'])
    REQUIRED = True
    MULTI_VALUE = False
    SECRET = False

    @classmethod
    def _init_cls(cls) -> None:
        super()._init_cls()

        data: list[dict[str, Any]] = [
            {'value': "Practice Tier"},
            {'value': "Beginner"},
            {'value': "Intermediate"},
            {'value': "Advanced"},
            {'value': "Expert"},
            {'value': "Master"},
            {'value': "Low Elite"},
            {'value': "Mid Elite"},
            {'value': "High Elite"},
            {'value': "Insanity Elite"},
            {'value': "God Tier"},
            {'value': "Hell Tier"},
            {'value': "Unproven"}
        ]

        for elem in data:
            first_part, has_space, _ = elem['value'].partition(" ")

            elem['alias'] = frozenset([first_part] if has_space else [])
        
        cls._add_raw_data(*data)


class Difficulty(AttrStrBundle):
    LOOKUP: dict[str | int | None, 'Difficulty'] = {}

    ALIAS: frozenset[str] = frozenset(['diff', 'd'])
    REQUIRED = True
    MULTI_VALUE = False
    SECRET = False

    def __init__(self, value: Opt[str], *, tier: Opt[Tier] = None, id: int, sort_value: int, missing: bool = True, alias: frozenset[str] = frozenset()):
        self.tier = TierSub(Tier.get(tier))
        self.missing: bool = missing
        super().__init__(value, id=id, sort_value=sort_value, alias=alias)

    @classmethod
    def _init_cls(cls) -> None:
        super()._init_cls()

        data: list[dict[str, Any]] = [
            {'value': "0/10", 'tier': Tier.get('Practice Tier')},
            {'value': "0.5/10", 'tier': Tier.get('Beginner')},
            {'value': "1/10", 'tier': Tier.get('Beginner')},
            {'value': "1.5/10", 'tier': Tier.get('Beginner')},
            {'value': "2/10", 'tier': Tier.get('Beginner')},
            {'value': "2.5/10", 'tier': Tier.get('Beginner')},
            {'value': "3/10", 'tier': Tier.get('Beginner')},
            {'value': "3.5/10", 'tier': Tier.get('Intermediate')},
            {'value': "4/10", 'tier': Tier.get('Intermediate')},
            {'value': "4.5/10", 'tier': Tier.get('Intermediate')},
            {'value': "5/10", 'tier': Tier.get('Intermediate')},
            {'value': "5.5/10", 'tier': Tier.get('Advanced')},
            {'value': "6/10", 'tier': Tier.get('Advanced')},
            {'value': "6.5/10", 'tier': Tier.get('Advanced')},
            {'value': "7/10", 'tier': Tier.get('Expert')},
            {'value': "7.5/10", 'tier': Tier.get('Expert')},
            {'value': "8/10", 'tier': Tier.get('Expert')},
            {'value': "8.5/10", 'tier': Tier.get('Master')},
            {'value': "9/10", 'tier': Tier.get('Master')},
            {'value': "9.5/10", 'tier': Tier.get('Master')},
            {'value': "10/10", 'tier': Tier.get('Master')},
            {'value': "Low Elite", 'tier': Tier.get('Low Elite')},
            {'value': "Mid Elite", 'tier': Tier.get('Mid Elite')},
            {'value': "High Elite", 'tier': Tier.get('High Elite')},
            {'value': "Insanity Elite", 'tier': Tier.get('Insanity Elite')},
            {'value': "God Tier", 'tier': Tier.get('God Tier')},
            {'value': "Hell Tier", 'tier': Tier.get('Hell Tier')},
            {'value': "Unproven", 'tier': Tier.get('Unproven')}
        ]

        for elem in data:
            # if not unproven, make 'missing' = True
            elem['missing'] = elem is not data[-1]

            v: str = elem['value']
            elem['alias'] = set()

            n, is_oo10, _ = v.partition("/")

            # -- Add aliases --
            # case x/10
            if is_oo10:
                elem['alias'] |= {n}
                
                # case .5
                if "." in n:
                    n_comma = n.replace(".", ",")
                    elem['alias'] |= {n_comma, n_comma + "/10"}

                    # case 0.5
                    if n == "0.5":
                        elem['alias'] |= {".5", ",5", ".5/10", ",5/10"}

            # case Elite and higher
            elif " " in v:
                elem['alias'] |= {v.partition(" ")[0]}

            elem['alias'] = frozenset(elem['alias'])
            
        cls._add_raw_data(*data)
        

class Type(AttrStr):
    MAX_LENGTH = 100
    LOOKUP: dict[str | int | None, 'Type'] = {}

    ALIAS: frozenset[str] = frozenset(["t", "ty", "typ"])
    REQUIRED = False
    MULTI_VALUE = True
    SECRET = False

    # @classmethod
    # def _init_cls(cls) -> None:
    #     super()._init_cls()

    #     data: list[dict[str, Any]] = []

    #     cls._add_raw_data(*data)


class Server(AttrStrBundle):
    LOOKUP: dict[str | int | None, 'Server'] = {}

    ALIAS: frozenset[str] = frozenset(["s", "serv"])
    REQUIRED = True
    MULTI_VALUE = False
    SECRET = False

    @classmethod
    def _init_cls(cls) -> None:
        super()._init_cls()

        data: list[dict[str, Any]] = [{
            'value': "SMO Trickjumping Server", 
            'alias': frozenset([
                "Main",         
                "Main Server",
                "Main Trickjump Server",
                "Main Trickjumping Server",
                "SMO Trickjump",
                "SMO Trickjump Server",
                "SMO Trickjumping",
                "Trickjump Server",
                "Trickjumping Server"
            ])}, {
            'value': "Database", 
            'alias': frozenset([
                "DB",
                "Database Server",
                "SMO Database",
                "SMO Trickjumping Database",
                "Trickjump Database",
                "Trickjumping Database",
                "Trickjump DB",
                "Trickjumping DB",
            ])
        }]
        cls._add_raw_data(*data)



class Finder(AttrPerson):
    ACTION = "Found"

    ALIAS: frozenset[str] = frozenset(["f", "founder", "find", "found"])
    REQUIRED = False
    MULTI_VALUE = True
    SECRET = False


class Taser(AttrPerson):
    ACTION = "TASed"

    ALIAS: frozenset[str] = frozenset(["tas", "tased"])
    REQUIRED = False
    MULTI_VALUE = True
    SECRET = False


class Prover(AttrPerson):
    ACTION = "Proven"

    ALIAS: frozenset[str] = frozenset(["p", "prov", "proven"])
    REQUIRED = False
    MULTI_VALUE = True
    SECRET = False


class FoundAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["fa", "f_a", "f_at", "foundat"])
    REQUIRED = False
    MULTI_VALUE = False
    SECRET = False


class TasedAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ta", "t_a", "tat", "t_at", "tas_at", "tasat", "tasedat"])
    REQUIRED = False
    MULTI_VALUE = False
    SECRET = False


class ProvenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["pa", "p_a", "pat", "p_at", "provat", "prov_at", "provenat"])
    REQUIRED = False
    MULTI_VALUE = False
    SECRET = False


class GivenAt(AttrDatetime):
    ALIAS: frozenset[str] = frozenset(["ga", "g_a", "gat", "g_at", "giveat", "give_at", "givenat"])
    REQUIRED = False
    MULTI_VALUE = False
    SECRET = False


class Proof(AttrStr):
    ALIAS: frozenset[str] = frozenset(["prof", "prove", "proven"])
    REQUIRED = False
    MULTI_VALUE = False
    SECRET = False

    MAX_LENGTH = MAX_LINK_LENGTH


class Link(AttrStr):
    ALIAS: frozenset[str] = frozenset(["l", "lnk", "clip", "video", "links"])
    REQUIRED = True
    MULTI_VALUE = True
    SECRET = False

    MAX_LENGTH = MAX_LINK_LENGTH

    def __init__(self, value: Opt[str], *, author: Opt[Person] = None):
        self.author = AuthorSub(author)
        super().__init__(value)


class Info(AttrStr):
    ALIAS: frozenset[str] = frozenset(["ex", "e", "extra", "i", "desc", "description", "data"])
    REQUIRED = False
    MULTI_VALUE = False
    SECRET = False

    MAX_LENGTH = 2048

    def __init__(self, value: Opt[str]):
        if value is not None:
            value = value.replace("\\n", "\n")

        super().__init__(value)

class Tag(AttrStrBundle):
    LOOKUP: dict[str | int | None, "Tag"] = {}

    ALIAS: frozenset[str] = frozenset(["tags"])
    REQUIRED = False
    MULTI_VALUE = True
    SECRET = False

class Thumbnail(AttrStr):
    ALIAS: frozenset[str] = frozenset(["tn", "thumb", "t_n", "th", "tnail"])
    REQUIRED = False
    MULTI_VALUE = False
    SECRET = True

    MAX_LENGTH = MAX_LINK_LENGTH


@dataclass(init=False, slots=True)
class AttrCollection:
    """
    A parent class for any class that wants to use attributes
    as its fields and provides functionality for that case.
    """
    __annotations__: CV[dict[str, type[AttrNormalT]]]
    
    def __init__(self, data: dict[str, Any], *, required: bool = True, lower: bool = True) -> None:
        attr_to_v: dict[str, Any] = {}

        for syn, v in data.items():
            try:
                attr: str = syn_to_name(syn, lower=lower)
                
                if attr not in self.__class__.field_names():
                    raise KeyError()
            except KeyError:
                raise fbe.InvalidAttribute(syn)
            
            if attr in attr_to_v:
                raise fbe.SameAttribute(syn)

            attr_to_v[attr] = v
        
        missing_attrs: list[str] = []

        for cls, is_multi in self.field_value_type_info().items():
            v = attr_to_v.get(cls.NAME, None)

            if v is None and required and cls.REQUIRED:
                missing_attrs.append(cls.NAME)

            setattr(
                self, 
                cls.NAME,
                AttrMultiValue.get(v, cls) if is_multi else cls.get(v)
            )

        if missing_attrs:
            raise fbe.RequiredAttributesMissing(missing_attrs)
    
    def mapping(self, predicate: Opt[Callable[[str, AttrNormalT], bool]] = None) -> dict[str, AttrNormalT]:
        if predicate is None:
            return {f.name: getattr(self, f.name) for f in self.fields()}
        return {k: v for k, v in self.mapping().items() if predicate(k, v)}
    
    @functools.cache
    def keys(self, predicate: Opt[Callable[[str, AttrNormalT], bool]] = None) -> KeysView[str]:
        return self.mapping(predicate).keys()
    
    def values(self, predicate: Opt[Callable[[str, AttrNormalT], bool]] = None) -> ValuesView[AttrNormalT]:
        return self.mapping(predicate).values()
    
    def items(self, predicate: Opt[Callable[[str, AttrNormalT], bool]] = None) -> ItemsView[str, AttrNormalT]:
        return self.mapping(predicate).items()

    _fields: CV[Opt[tuple[Field, ...]]] = None

    @classmethod
    def fields(cls) -> tuple[Field, ...]:
        if cls._fields is None:
            cls._fields = fields(cls)
        return cls._fields
    
    _field_names: CV[Opt[tuple[str, ...]]] = None

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        if cls._field_names is None:
            cls._field_names = tuple(f.name for f in cls.fields())
        return cls._field_names
    
    _field_types: CV[Opt[dict[str, type[AttrNormalT]]]] = None

    @classmethod
    def field_types(cls) -> dict[str, type[AttrNormalT]]:
        if cls._field_types is None:
            resolved_hints = typing.get_type_hints(cls, globals(), locals())
            
            cls._field_types = {
                name: resolved_hints[name] for name in cls.field_names()
            }
        return cls._field_types
    
    _field_value_type_info: CV[Opt[dict[type[AttrSingleValue], bool]]] = None

    @classmethod
    def field_value_type_info(cls) -> dict[type[AttrSingleValue], bool]:
        """dict[value_cls, is_AttrMultiValue]"""
        if cls._field_value_type_info is None:
            type_info: dict[type[AttrSingleValue], bool] = {}

            for v in cls.field_types().values():
                if _issubclass(v, AttrSingleValue):
                    type_info[v] = False  # type: ignore
                elif _issubclass(get_origin(v), AttrMultiValue):
                    type_info[get_args(v)[0]] = True
                else:
                    raise TypeError

            cls._field_value_type_info = type_info

        return cls._field_value_type_info
    
    def get_attr(self, attr: str | type[AttrSingleValue]) -> AttrNormalT:
        if isinstance(attr, str):
            name: str = attr
        else:
            name: str = attr.NAME
        return getattr(self, name)

    def set_attr(self, attr: str | type[AttrSingleValue], value: Any) -> AttrNormalT:
        if isinstance(attr, str):
            cls = syn_to_cls(attr)
        else:
            cls = attr
        
        name: str = cls.NAME
        instance: AttrSingleValue = cls.get(value)

        result: AttrNormalT = AttrMultiValue.get(instance, cls) if cls.MULTI_VALUE else instance

        setattr(self, name, result)
        return result

    def pop(self, attr: str | type[AttrSingleValue]) -> AttrNormalT:
        value: AttrNormalT = self.get_attr(attr)
        setattr(self, value.value_cls.NAME, value.__class__.get(None, value.value_cls))
        return value
    
    def get_attr_hierarchy_value(self, expression: str, predicate: Callable[[AttrAny], bool]) -> Any:
        parts: list[str] = [stripped for part in expression.split(".") if (stripped := part.strip())]
        
        if not parts:
            raise ValueError()
        
        for i, part in enumerate(parts):
            # try converting attrs from syn to name
            try:
                parts[i] = syn_to_name(part, True)
            except KeyError:
                part = part.casefold()

        curr_obj: Any = self.get_attr(parts[0])
        # expression = ".".join(parts)

        for i, part in enumerate(parts):
            try:
                if not isinstance(curr_obj, AttrAny):
                    raise AttributeError()
                
                if not predicate(curr_obj):
                    raise AttributeError()
                
                # possibly raises AttributeError if doesn't exist
                curr_obj = getattr(curr_obj, part)

                if isinstance(curr_obj, AttrSub):
                    curr_obj = curr_obj.value
            except (AttributeError, KeyError):
                if i == 0:
                    raise fbe.InvalidAttribute(part, expression=expression)
                else:
                    raise fbe.InvalidSubAttribute(parts[i - 1], part, expression=expression)

        curr_obj = curr_obj.value

        return curr_obj
    

# TODO turn into metaclass
def _init_module():
    def recursively_iterate_subclasses[T](cls: type[T], do: Callable[[type[T]], None]):
        do(cls)

        for subclass in cls.__subclasses__():
            recursively_iterate_subclasses(subclass, do)

    recursively_iterate_subclasses(AttrSingleValue, lambda cls: cls._init_cls())

    def integrity_check_attribute_collection_subclasses(cls: type[AttrCollection]):
        # TODO
        ...

    recursively_iterate_subclasses(AttrCollection, integrity_check_attribute_collection_subclasses)

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