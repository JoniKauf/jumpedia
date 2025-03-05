

import ast
from collections import Counter
import json
import sys
from typing import Any, Callable, Hashable, Iterable, Literal, Optional as Opt, Self, Sequence
from enum import Enum
from discordtools import feedbackerrors as fbe
from people.person import Person
import re

type ContextT = str
type AttrT = '_AttributeBase'
TMP_CTX = "Jumpedia"

#------#   Module Constants   #------#

_ATTR_LOOKUP: dict[ContextT, dict[str, '_AttributeBase']] = {}
_ALL_ATTRS: dict[ContextT, list['_AttributeBase']] = {}
_ALL_ATTRIBUTE_TYPES: list[type['_AttributeBase']] = []

_NAME_CONVERSION_PATTERN = re.compile(r'(?!^)([A-Z]+)')

#------#   Mixins   #------#

class _AttributePluralMixin[T]:
    def __init__(
        self,
        max: int,
        max_duplicates: int
    ) -> None:
        self._max = max if max >= 0 else 0
        self._max_duplicates = max_duplicates if max_duplicates >= 1 else 1

    @property
    def max_duplicates(self) -> int:
        return self._max_duplicates
    
    @property
    def max(self) -> int:
        return self._max
    
    def _from_str(self, value: Opt[str]) -> Opt[list[T]]:
        if value is None or not (value := value.strip()):
            return None

        v: list[str] = json.loads(value)

        if not isinstance(v, list):
            raise Exception
        
        if self.max > 0 and len(v) > self.max:
            raise Exception
        
        counter: Counter[T] = Counter()
        unfiltered_v = v
        filtered_v: list[T] = []

        for elem in unfiltered_v:
            if not isinstance(elem, str):
                raise Exception
            
            elem = super(self.__class__, self)._from_str(elem)  # type: ignore
            
            if elem is None:
                continue
                
            if elem not in counter:
                counter[elem] = 1
            else:
                counter[elem] += 1

            if counter[elem] > self.max_duplicates:
                raise fbe.TemporaryFeedbackError

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
        unique: bool,
        required: bool,
        hidden: bool
    ):
        name = name.casefold().strip()
        alias = frozenset(a.casefold().strip() for a in alias)

        lookup = _ATTR_LOOKUP.setdefault(context, {})
        _ALL_ATTRS.setdefault(context, []).append(self)

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
        self._required = required
        self._unique = unique
        self._hidden = hidden

        for syn in (name, *alias):
            lookup[syn] = self

    @classmethod
    def __init_subclass__(cls) -> None:
        cls.TYPE = re.sub(_NAME_CONVERSION_PATTERN, r' \1', cls.__name__)
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
    def required(self) -> bool:
        return self._required
    
    @property
    def unique(self) -> bool:
        return self._unique
    
    @property
    def hidden(self) -> bool:
        return self._hidden

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
        required: bool,
        unique: bool,
        hidden: bool, 
        collection: Sequence[str],
    ):
        super().__init__(
            context=context,
            name=name, 
            alias=alias, 
            required=required,
            unique=unique,
            hidden=hidden
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
        required: bool,
        unique: bool,
        hidden: bool, 
        max: int,
        max_duplicates: int,
    ):
        super().__init__(
            context=context,
            name=name, 
            alias=alias, 
            required=required,
            unique=unique,
            hidden=hidden 
        )

        _AttributePluralMixin.__init__(
            self,
            max=max,
            max_duplicates=max_duplicates
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
        required: bool, 
        unique: bool,
        hidden: bool, 
        collection: Sequence[str],
        max: int,
        max_duplicates: int
    ):
        super().__init__(
            context=context,
            name=name,
            alias=alias,
            required=required,
            unique=unique,
            hidden=hidden,
            collection=collection
        )

        _AttributePluralMixin.__init__(
            self, 
            max=max,
            max_duplicates=max_duplicates
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
        required: bool,
        unique: bool,
        hidden: bool, 
        max: int,
        max_duplicates: int
    ):
        super().__init__(
            context=context, 
            name=name, 
            alias=alias, 
            required=required,
            unique=unique,
            hidden=hidden, 
        )

        _AttributePluralMixin.__init__(
            self, 
            max=max,
            max_duplicates=max_duplicates
        )

    def _from_str(self, value: Opt[str]) -> Opt[list[Person]]:
        return _AttributePluralMixin._from_str(self, value)


#------#   Module Functionality   #------#

def get(context: ContextT, attr: str) -> _AttributeBase:
    try:
        lookup = _ATTR_LOOKUP[context]
    except KeyError:
        raise fbe.TemporaryFeedbackError
    
    try:
        return lookup[attr]
    except KeyError:
        raise fbe.InvalidAttribute(attr)

def get_all(context: ContextT) -> tuple[_AttributeBase, ...]:
    return tuple(_ALL_ATTRS[context])
    

if __name__ == '__main__':
    print(_ALL_ATTRIBUTE_TYPES)
    print(_ATTR_LOOKUP)

    attr = AttributePluralStr(TMP_CTX, "test", ["test"], True, True, True, 10, 100)
    print(attr._from_str(f'["test", "{"a" * 1025}"]'))