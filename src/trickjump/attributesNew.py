

import ast
import json
import sys
from typing import Any, Callable, Hashable, Iterable, Literal, Optional as Opt, Self, Sequence
from enum import Enum
from discordtools import feedbackerrors as fbe
from people.person import Person
import re

type ContextT = Hashable

#------#   Module Constants   #------#

_ATTR_LOOKUP: dict[ContextT, dict[str, '_AttributeBase']] = {}
_NAME_CONVERSION_PATTERN = re.compile(r'(?!^)([A-Z]+)')
_ALL_ATTRIBUTE_TYPES: list[type['_AttributeBase']] = []

#------#   Mixins   #------#

class _AttributePluralMixin[T]:
    def __init__(
        self,
        unique: bool,
        limit: int
    ) -> None:
        self._unique = unique
        self._limit = limit if limit > 0 else 0

    @property
    def unique(self) -> bool:
        return self._unique
    
    @property
    def limit(self) -> int:
        return self._limit
    
    def _from_str(self, value: Opt[str]) -> Opt[list[T]]:
        if value is None or not (value := value.strip()):
            return None

        v: list[str] = json.loads(value)

        if not isinstance(v, list):
            raise Exception
        
        if self.limit > 0 and len(v) > self.limit:
            raise Exception
        
        used: set[str] = set()
        unfiltered_v = v
        filtered_v: list[T] = []

        for elem in unfiltered_v:
            if not isinstance(elem, str):
                raise Exception
            
            elem = super(self.__class__, self)._from_str(elem)
            
            if elem is None:
                continue

            if self.unique:
                if elem in used:
                    raise Exception
                
                used.add(elem)

            filtered_v.append(elem)

        return filtered_v or None


#------#   AttributeBase   #------#

class _AttributeBase[T]:
    VALID_CHARS: set[str] = set('abcdefghijklmnopqrstuvwxyz_0123456789')

    def __init__(
        self, 
        context: ContextT,
        name: str,
        alias: Iterable[str],
        hidden: bool,
        required: bool
    ):
        name = name.casefold().strip()
        alias = frozenset(a.casefold().strip() for a in alias)

        lookup = _ATTR_LOOKUP.setdefault(context, {})
        
        for syn in (name, *alias):
            if syn in lookup:
                raise ValueError(
                    f"Attribute name or alias '{syn}' already in use"
                )
            
            if not syn:
                raise ValueError("Empty attribute name")
            
            for char in syn:
                if char not in self.__class__.VALID_CHARS:
                    raise ValueError("Invalid char: ", char)
        
        self._context = context
        self._name = name
        self._alias = alias
        self._hidden = hidden
        self._required = required

        for syn in (name, *alias):
            lookup[syn] = self

    @classmethod
    def __init_subclass__(cls) -> None:
        cls.TYPE = re.sub(_NAME_CONVERSION_PATTERN, r'_\1', cls.__name__).lower()
        _ALL_ATTRIBUTE_TYPES.append(cls)

    @property
    def context(self) -> ContextT:
        return self._context
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def alias(self) -> frozenset[str]:
        return self._alias
    
    @property
    def hidden(self) -> bool:
        return self._hidden

    @property
    def required(self) -> bool:
        return self._required
    
    def is_empty(self, value: Opt[str]) -> bool:
        return self._from_str(value) is None
    
    def _from_str(self, value: Opt[str]) -> Opt[T]:
        raise NotImplementedError()
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        raise NotImplementedError()
    

#------#   Attribute Specific Implementations   #------#

class AttributeBool(_AttributeBase[bool]):
    def _from_str(self, value: Opt[str]) -> Opt[bool]:
        if value is None or not (value := value.strip()):
            return None
        
        value = value.lower()

        if value == "true":
            return True
        if value == "false":
            return False
        
        raise fbe.NotAProperValue("boolean", value)
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return 2 * sign
        
        return (not v) * sign
    

class AttributeInt(_AttributeBase[int]):
    MIN_INT: int = -(2 ** 64)
    MAX_INT: int = 2 ** 64 - 1
    MAX_INT_STR: int = len(str(MAX_INT)) 

    def _from_str(self, value: Opt[str]) -> Opt[int]:
        if value is None or not (value := value.strip()):
            return None
        
        if len(value) > self.__class__.MAX_INT_STR:
            raise fbe.OutsideOfValidRange(
                value, self.__class__.MIN_INT, self.__class__.MAX_INT
            )
        
        try:
            result = int(value)
        except ValueError:
            raise fbe.NotAProperValue("integer", value)

        if not (self.__class__.MIN_INT < result < self.__class__.MAX_INT):
            raise fbe.OutsideOfValidRange(
                result, self.__class__.MIN_INT, self.__class__.MAX_INT
            )
        
        return result

    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            v = self.MAX_INT + 1
            
        return v * sign
    

class AttributeStr(_AttributeBase[str]):
    MAX_STR_LEN = 2 ** 10

    def _from_str(self, value: Opt[str]) -> Opt[str]:
        if value is None or not (value := value.strip()):
            return None
        
        if len(value) > self.__class__.MAX_STR_LEN:
            raise fbe.TooLongValue("string", value, self.__class__.MAX_STR_LEN)
        
        return value

    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return ((sys.maxunicode + 1) * sign,)
        
        if not case_sensitive:
            v = v.casefold()

        return tuple(ord(char) * sign for char in v)


class AttributeStrCollection(AttributeStr):
    MAX_COLLECTION_LEN = 2 ** 12

    def __init__(
        self, 
        context: ContextT,
        name: str, 
        alias: Iterable[str], 
        hidden: bool, 
        required: bool,
        collection: Sequence[str],
    ):
        super().__init__(
            context=context,
            name=name, 
            alias=alias, 
            hidden=hidden, 
            required=required
        )

        # dict[casefolded_val, tuple[val, index]]
        self._collection: dict[str, tuple[str, int]] = {}

        if len(collection) > self.__class__.MAX_COLLECTION_LEN:
            raise fbe.TooManyCollectionElements(
                self.name, self.__class__.MAX_COLLECTION_LEN
            )
        
        for i, elem in enumerate(collection):
            elem = elem.strip()
            elem_cf = elem.casefold()
            
            if elem_cf in collection:
                raise fbe.CollectionElementCollision(self.name, elem_cf)
            
            self._collection[elem_cf] = (elem, i)

    @property
    def collection(self) -> dict[str, tuple[str, int]]:
        return self._collection
    
    def _from_str(self, value: Opt[str]) -> Opt[str]:
        v = super()._from_str(value)

        if v is None:
            return None
        
        if v not in self.collection:
            raise fbe.NotPartOfTheCollection(self.name, v)
        
        return v.casefold()
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return len(self.collection) * sign
        
        return self.collection[v][1] * sign


class AttributePerson(_AttributeBase[Person]):
    MAX_PERSON_NAME_LEN = Person.MAX_PERSON_NAME_LEN

    def _from_str(self, value: Opt[str]) -> Opt[Person]:
        if value is None or not (value := value.strip()):
            return None
        
        return Person.get(value)
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return None
        
        name: str = v.name if case_sensitive else v.name.casefold()

        return tuple(ord(char) * sign for char in name)


#------#   Attribute Plural Implementations   #------#

class AttributePluralStr(AttributeStr, _AttributePluralMixin[str]):
    def __init__(
        self, 
        context: ContextT,
        name: str, 
        alias: Iterable[str], 
        hidden: bool, 
        required: bool,
        unique: bool,
        limit: int
    ):
        super().__init__(
            context=context,
            name=name, 
            alias=alias, 
            hidden=hidden, 
            required=required
        )

        _AttributePluralMixin.__init__(
            self,
            unique=unique, 
            limit=limit
        )
    
    def _from_str(self, value: Opt[str]) -> Opt[list[str]]:
        return _AttributePluralMixin._from_str(self, value)
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return (((sys.maxunicode + 1) * sign,),)
        
        return tuple(
            tuple(ord(char) * sign for char in (
                s if case_sensitive else s.casefold()
            )) 
            for s in v
        )

class AttributePluralStrCollection(AttributeStrCollection, _AttributePluralMixin[str]):
    def __init__(
        self, 
        context: ContextT,
        name: str, 
        alias: Iterable[str], 
        hidden: bool, 
        required: bool, 
        collection: Sequence[str],
        unique: bool, 
        limit: int = 0
    ):
        super().__init__(
            context=context,
            name=name,
            alias=alias,
            hidden=hidden,
            required=required,
            collection=collection
        )

        _AttributePluralMixin.__init__(
            self, 
            unique=unique,
            limit=limit
        )

    def _from_str(self, value: Opt[str]) -> Opt[list[str]]:
        return _AttributePluralMixin._from_str(self, value)
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return (len(self.collection) * sign,)
        
        return tuple(
            self.collection[elem][1] for elem in v
        )
    

class AttributePluralPerson(AttributePerson, _AttributePluralMixin[Person]):
    def __init__(
        self, 
        context: ContextT, 
        name: str, 
        alias: Iterable[str], 
        hidden: bool, 
        required: bool,
        unique: bool,
        limit: int
    ):
        super().__init__(
            context=context, 
            name=name, 
            alias=alias, 
            hidden=hidden, 
            required=required
        )

        _AttributePluralMixin.__init__(
            self, 
            unique=unique, 
            limit=limit
        )

    def _from_str(self, value: Opt[str]) -> Opt[list[Person]]:
        return _AttributePluralMixin._from_str(self, value)


#------#   Module Functionality   #------#

def get(context: ContextT, attr: str) -> _AttributeBase:
    try:
        lookup = _ATTR_LOOKUP[context]
    except KeyError:
        raise Exception
    
    try:
        return lookup[attr]
    except KeyError:
        raise fbe.InvalidAttribute(attr)