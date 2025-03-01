

import sys
from typing import Any, Callable, Iterable, Literal, Optional as Opt, Sequence
from enum import Enum
from discordtools import feedbackerrors as fbe


class Attribute[T]:
    VALID_CHARS: set[str] = set('abcdefghijklmnopqrstuvwxyz_0123456789')

    _attr_lookup: dict[str, 'Attribute'] = {}

    def __init__(
        self, 
        *,
        name: str,
        alias: Iterable[str],
        hidden: bool,
        required: bool
    ):
        name = name.casefold().strip()
        alias = frozenset(a.casefold().strip() for a in alias)

        for syn in (name, *alias):
            if syn in self.__class__._attr_lookup:
                raise ValueError(
                    f"Attribute name or alias '{syn}' already in use"
                )
            
            if not syn:
                raise ValueError("Empty attribute name")
            
            for char in syn:
                if char not in self.__class__.VALID_CHARS:
                    raise ValueError("Invalid char: ", char)
                             
        self._name = name
        self._alias = alias
        self._hidden = hidden
        self._required = required

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
    
    @classmethod
    def get(cls, attr: str) -> 'Attribute':
        try:
            return cls._attr_lookup[attr]
        except KeyError:
            raise fbe.InvalidAttribute(attr)
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1]):
        raise NotImplementedError()
    
    def _from_str(self, value: Opt[str]) -> Opt[T]:
        raise NotImplementedError()


class _AttributeBool(Attribute[bool]):
    def _from_str(self, value: Opt[str]) -> Opt[bool]:
        if value is None:
            return None
        
        value = value.lower()

        if value == "true":
            return True
        if value == "false":
            return False
        
        raise fbe.NotAProperValue("boolean", value)
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1]):
        v = self._from_str(value)

        if v is None:
            return 2 * sign
        
        return (not v) * sign
    

class _AttributeInt(Attribute[int]):
    MIN_INT: int = -(2 ** 64)
    MAX_INT: int = 2 ** 64 - 1
    MAX_INT_STR: int = len(str(MAX_INT)) 

    def _from_str(self, value: Opt[str]) -> Opt[int]:
        if value is None:
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

    def sort_key(self, value: Opt[str], sign: Literal[+1, -1]):
        v = self._from_str(value)

        if v is None:
            v = self.MAX_INT + 1
            
        return v * sign
    

class _AttributeStr(Attribute[str]):
    MAX_STR_LEN = 2 ** 12

    def _from_str(self, value: Opt[str]) -> Opt[str]:
        if not value:
            return None
        
        if len(value) > self.__class__.MAX_STR_LEN:
            raise fbe.TooLongValue("string", value, self.__class__.MAX_STR_LEN)
        
        return value

    def sort_key(self, value: Opt[str], sign: Literal[+1, -1]):
        v = self._from_str(value)

        if v is None:
            return (sys.maxunicode + 1,) * sign
        
        return tuple(ord(char) * sign for char in v)


class _AttributeStrCollection(_AttributeStr):
    MAX_COLLECTION_LEN = 2 ** 12

    def __init__(
        self, 
        *, 
        name: str, 
        alias: Iterable[str], 
        hidden: bool, 
        required: bool,
        collection: Sequence[str]
    ):
        super().__init__(
            name=name, 
            alias=alias, 
            hidden=hidden, 
            required=required
        )

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
        value = super()._from_str(value)

        if value is None:
            return None
        
        if value not in self.collection:
            raise fbe.NotPartOfTheCollection(self.name, value)
        
        return value.casefold()
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1]):
        v = self._from_str(value)

        if v is None:
            return 
        
        return self.collection[v][1] * sign
    

class _AttributeStrPlural(Attribute[str]):
    # TODO allow UNIQUE
    ...

class _AttributeStrPluralCollection(Attribute[str]):
    ...