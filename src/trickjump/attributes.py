

import ast
from collections import Counter, defaultdict
import json
import sys
from typing import Any, Callable, Hashable, Iterable, Literal, Optional as Opt, Self, Sequence
from enum import Enum
from discordtools import feedbackerrors as fbe
from people.person import Person
import re
from collections2 import tree as tree_

type ContextT = str
type AttrT = '_AttributeBase'
type TreeT[T: Hashable] = dict[T, TreeT[T]]


TMP_CTX = "Jumpedia"

#------#   Module Constants & Helper Functions   #------#

_ATTR_LOOKUP: dict[ContextT, dict[str, '_AttributeBase']] = {}
_ALL_ATTRS: dict[ContextT, list['_AttributeBase']] = {}
_ALL_ATTRIBUTE_TYPES: list[type['_AttributeBase']] = []

_RECURSION_LIMIT = 2 ** 6

_NAME_CONVERSION_PATTERN = re.compile(r'(?!^)([A-Z]+)')
_DUPLICATE_WHITESPACE_PATTERN = re.compile(r'\s+')
_VALID_CHARS: set[str] = set('abcdefghijklmnopqrstuvwxyz_0123456789')


def normalize_syn(syn: str, context: ContextT) -> str:
    syn = re.sub(_DUPLICATE_WHITESPACE_PATTERN, '_', syn.lower().casefold())

    if not syn:
        raise fbe.TemporaryFeedbackError
    
    if len(syn) > _AttributeBase.MAX_SYN_LEN:
        raise fbe.TemporaryFeedbackError
    
    illegals: set[str] = set()

    for char in syn:
        if char not in _VALID_CHARS:
            illegals.add(char)

    if illegals:
        raise fbe.TemporaryFeedbackError(illegals)
    
    if syn in _ATTR_LOOKUP.get(context, {}):
        raise fbe.TemporaryFeedbackError
    
    return syn

#hello schatz i love you

# def _tree_worker[T: Hashable](tree: TreeT[T], normalize: Callable[[T], T]) -> tuple[dict[T, set[T]], dict[T, T]]:
#     children: dict[T, set[T]] = {}
#     unnormalize: dict[T, T] = {}
#     all_visited: set[T] = set()

#     def _visit_node(node_names: tuple[T, T], child_nodes: TreeT[T], depth: int):
#         if depth > _RECURSION_LIMIT:
#             raise fbe.TemporaryFeedbackError

#         node_name, norm_node_name = node_names
        
#         # Check if duplicate node, otherwise add to collection 
#         if norm_node_name in all_visited:
#             raise fbe.TemporaryFeedbackError("Cyclic")
        
#         all_visited.add(norm_node_name)
        
#         unnormalize[norm_node_name] = node_name

#         for child_node_name, child_child_nodes in child_nodes.items():
#             norm_child_node_name = normalize(child_node_name)
                
#             children.setdefault(norm_node_name, set()).add(norm_child_node_name)
            
#             _visit_node(
#                 (child_node_name, norm_child_node_name), 
#                 child_child_nodes, 
#                 depth + 1
#             )

#     for child_node_name, child_child_nodes in tree.items():
#         norm_child_node_name = normalize(child_node_name)

#         _visit_node(
#             (child_node_name, norm_child_node_name), 
#             child_child_nodes, 
#             1
#         )

#     return children, unnormalize

    
def _get_plural_from_str_method[TParent](
    singular_from_str: Callable[[Any, Opt[str]], Opt[TParent]]
) -> Callable[[Any, Opt[str]], Opt[list[TParent]]]:

    def _from_str(self, value: Opt[str]) -> Opt[list[TParent]]:
        if value is None or not (value := value.strip()):
            return None

        v: list[str] = json.loads(value)

        if not isinstance(v, list):
            raise Exception
        
        if self.max > 0 and len(v) > self.max:
            raise Exception
        
        counter: Counter[TParent] = Counter()
        unfiltered_v = v
        filtered_v: list[TParent] = []

        for elem in unfiltered_v:
            if not isinstance(elem, str):
                raise Exception
            
            elem = singular_from_str(self, elem)
            
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
    
    return _from_str
    
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


#------#   AttributeBase   #------#

class _AttributeBase[T]:
    TYPE_ID: int
    MAX_SYN_LEN = 32

    def __init__(
        self, 
        context: ContextT,
        name: str,
        alias: Iterable[str],
        unique: bool,
        required: bool,
        hidden: bool,
        *other: *tuple[()]
    ):
        name = normalize_syn(name, context)
        alias = frozenset(normalize_syn(a, context) for a in alias)

        lookup = _ATTR_LOOKUP.setdefault(context, {})
        _ALL_ATTRS.setdefault(context, []).append(self)
        
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
    TYPE_ID = 1

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
    TYPE_ID = 2

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
    TYPE_ID = 3

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
    TYPE_ID = 4

    MAX_COLLECTION_LEN = 2 ** 12

    def __init__(
        self, 
        context: ContextT,
        name: str, 
        alias: Iterable[str], 
        required: bool,
        unique: bool,
        hidden: bool, 
        *args: *tuple[Sequence[str]]
    ):
        collection, = args             

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
    
class AttributeStrCollectionTree(_AttributeBase[str]):
    def __init__(
        self, 
        context: str, 
        name: str, 
        alias: Iterable[str], 
        required: bool, 
        unique: bool, 
        hidden: bool, 
        *args: *tuple[TreeT[str]]
    ):
        tree, = args

        self.tree = tree_.Tree(tree, lambda s: s.strip().casefold())
        input(self.tree)
        super().__init__(
            context, 
            name, 
            alias, 
            required, 
            unique, 
            hidden
        )



class AttributePerson(_AttributeBase[Person]):
    TYPE_ID = 5
    MAX_PERSON_NAME_LEN = Person.MAX_PERSON_NAME_LEN

    def _from_str(self, value: Opt[str]) -> Opt[Person]:
        if value is None or not (value := value.strip()):
            return None
        
        return Person.get(value)
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return ((sys.maxunicode + 1) * sign,)
        
        name: str = v.name if case_sensitive else v.name.casefold()

        return tuple(ord(char) * sign for char in name)


#------#   Attribute Plural Implementations   #------#

ATTRIBUTE_PLURAL_BASE_ID = 128

class AttributePluralStr(AttributeStr, _AttributePluralMixin[str]):
    TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributeStr.TYPE_ID

    def __init__(
        self, 
        context: ContextT,
        name: str, 
        alias: Iterable[str], 
        required: bool,
        unique: bool,
        hidden: bool, 
        *other: *tuple[int, int]
    ):
        max, max_duplicates = other

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
    
    _from_str: Callable[[Opt[str]], Opt[list[str]]] = _get_plural_from_str_method(AttributeStr._from_str)  # type: ignore
    
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
    TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributeStrCollection.TYPE_ID

    def __init__(
        self, 
        context: ContextT,
        name: str, 
        alias: Iterable[str], 
        required: bool, 
        unique: bool,
        hidden: bool,
        *other: *tuple[int, int, Sequence[str]]
    ):
        max, max_duplicates, collection = other

        super().__init__(
            context,
            name,
            alias,
            required,
            unique,
            hidden,
            *(collection,)
        )

        _AttributePluralMixin.__init__(
            self, 
            max=max,
            max_duplicates=max_duplicates
        )

    _from_str: Callable[[Opt[str]], Opt[list[str]]] = _get_plural_from_str_method(AttributeStrCollection._from_str)  # type: ignore
    
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return (len(self.collection) * sign,)
        
        return tuple(
            self.collection[elem][1] for elem in v
        )
    

class AttributePluralPerson(AttributePerson, _AttributePluralMixin[Person]):
    TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributePerson.TYPE_ID
    
    def __init__(
        self, 
        context: ContextT, 
        name: str, 
        alias: Iterable[str], 
        required: bool,
        unique: bool,
        hidden: bool,
        *other: *tuple[int, int]
    ):
        max, max_duplicates = other

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

    _from_str: Callable[[Opt[str]], Opt[list[Person]]] = _get_plural_from_str_method(AttributePerson._from_str)  # type: ignore
     
    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            return (((sys.maxunicode + 1) * sign,),)
        
        return tuple(
            tuple(ord(char) * sign for char in (
                person.name if case_sensitive else person.name.casefold()
            )) 
            for person in v
        )


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

    AttributeStrCollectionTree(
        TMP_CTX, 
        "test", 
        [], 
        True,
        True,
        True,
        {
            "Metro Kingdom": {
                "Tank Subarea": {
                    "Test1": {}
                },
                "Ogre Subarea": {}
            },
            "Dark Side": {
                "Broodal Fight 1": {}
            },
        }
    )
    # attr = AttributePluralStr(TMP_CTX, "test", ["test"], True, True, True, 10, 100)
    # print(attr._from_str(f'[""]'))