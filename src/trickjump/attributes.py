

import ast
from collections import Counter, defaultdict
from datetime import datetime
import functools
import json
import sys
from typing import Any, Callable, Hashable, Iterable, Literal, Optional as Opt, Self, Sequence, cast
from enum import Enum, auto
from discordtools import feedbackerrors as fbe
from people.person import Person
import re
from collections2 import tree as tree_
from trickjump.community import Community
import builtins

type AttrT = 'Attribute'
type TreeT[T: Hashable] = dict[T, TreeT[T]]

#------#   Module Constants & Helper Functions   #------#

_RECURSION_LIMIT = 2 ** 6

_NAME_CONVERSION_PATTERN = re.compile(r'(?!^)([A-Z]+)')
_DUPLICATE_WHITESPACE_PATTERN = re.compile(r'\s+')
_VALID_CHARS: set[str] = set('abcdefghijklmnopqrstuvwxyz_0123456789')
    
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

class AttributeStructure(Enum):
    SINGLE = auto()
    PLURAL = auto()
    TREE = auto()

class AttributeInteractability(Enum):
    HIDDEN = auto()
    SHOWN = auto()
    REQUIRED = auto()
    USER = auto()

#------#   Attribute   #------#

class Attribute[T: bool | int | float | str | datetime]:
    TYPE_ID: int
    MAX_SYN_LEN = 32
    MAX_ATTRIBUTES_PER_COMMUNITY = 50
    
    LOOKUP: defaultdict[Community, dict[str, 'Attribute']] = defaultdict(lambda: {})

    # Number (int | float)
    MIN_NUMBER: int = -(2 ** 64)
    MAX_NUMBER: int = 2 ** 64 - 1
    MAX_NUMBER_AS_STR_LEN: int = len(str(MAX_NUMBER)) 

    # String (str)
    MAX_STR_LEN = 1024

    def __init__(
        self, 
        community: Community,
        name: str,
        alias: Iterable[str],
        value_type: type[T],
        interactability: AttributeInteractability,
        structure: AttributeStructure,
        collection: Iterable[T],
        unique_in_list: bool
    ):
        if structure is AttributeStructure.TREE and not collection:
            raise fbe.TemporaryFeedbackError

        self.community = community
        self.name = self._normalize_syn(name)
        self.alias = set(self._normalize_syn(a) for a in alias)
        self.value_type = value_type
        self.interactability = interactability
        self.stucture = structure
        self.collection = {self._normalize_value(v): v for v in collection}
        self.unique_in_list = unique_in_list
    
    def _normalize_syn(self, syn: str) -> str:
        syn = re.sub(_DUPLICATE_WHITESPACE_PATTERN, '_', syn.strip().casefold())

        if not syn:
            raise fbe.TemporaryFeedbackError
        
        if len(syn) > self.__class__.MAX_SYN_LEN:
            raise fbe.TemporaryFeedbackError
        
        if syn in self.__class__.LOOKUP[self.community]:
            raise fbe.TemporaryFeedbackError
        
        illegal_chars: set[str] = set()

        for char in syn:
            if char not in _VALID_CHARS:
                illegal_chars.add(char)

        if illegal_chars:
            raise fbe.TemporaryFeedbackError(illegal_chars)
        
        return syn
            
    def is_empty(self, value: Opt[str]) -> bool:
        return self._from_str(value) is None
    
    def _normalize_value(self, value: T) -> T:
        match self.value_type:
            case builtins.str:
                return re.sub(_DUPLICATE_WHITESPACE_PATTERN, " ", value.strip().casefold())  # type: ignore
            case _:
                return value
            
    def _from_str(self, value: Opt[str], structure: Opt[AttributeStructure] = None) -> Opt[T]:
        if value is None or not (value := value.strip()):
            return None
        
        if structure is None:
            structure = self.stucture
        
        match self.value_type:
            case builtins.bool:
                value = value.lower()

                if value == "false":
                    result = False
                elif value == "true":
                    result = True
                else:
                    raise fbe.NotAProperValue("boolean", value)
            case builtins.int | builtins.float:
                if len(value) > self.__class__.MAX_NUMBER_AS_STR_LEN:
                    raise fbe.OutsideOfValidRange(value, self.__class__.MIN_NUMBER, self.__class__.MAX_NUMBER )

                try:
                    result = self.value_type(value)
                except ValueError:
                    raise fbe.NotAProperValue("number", value)

                if not (self.__class__.MIN_NUMBER < result < self.__class__.MAX_NUMBER):
                    raise fbe.OutsideOfValidRange(result, self.__class__.MIN_NUMBER, self.__class__.MAX_NUMBER)
            case builtins.str:
                if len(value) > self.__class__.MAX_STR_LEN:
                    raise fbe.TooLongValue("string", value, self.__class__.MAX_STR_LEN)
                
                result = re.sub(_DUPLICATE_WHITESPACE_PATTERN, " ", value)
            case _:
                raise ValueError

        return result  # type: ignore
            
    
            
    
            
        
    

#------#   Attribute Specific Implementations   #------#

class AttributeBool(Attribute[bool]):
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
    

class AttributeInt(Attribute[int]):
    TYPE_ID = 2

    

    def _from_str(self, value: Opt[str]) -> Opt[int]:
        if value is None or not (value := value.strip()):
            return None
        
        if len(value) > self.__class__.MAX_NUMBER_AS_STR_LEN:
            raise fbe.OutsideOfValidRange(
                value, self.__class__.MIN_NUMBER, self.__class__.MAX_NUMBER
            )
        
        try:
            result = int(value)
        except ValueError:
            raise fbe.NotAProperValue("integer", value)

        if not (self.__class__.MIN_NUMBER < result < self.__class__.MAX_NUMBER):
            raise fbe.OutsideOfValidRange(
                result, self.__class__.MIN_NUMBER, self.__class__.MAX_NUMBER
            )
        
        return result

    def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
        v = self._from_str(value)

        if v is None:
            v = self.MAX_NUMBER + 1
            
        return v * sign
    

class AttributeStr(Attribute[str]):
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
            unique_in_list=unique,
            interactability=hidden
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
    
class AttributeStrCollectionTree(Attribute[str]):
    def __init__(
        self, 
        context: str, 
        name: str, 
        alias: Iterable[str], 
        required: bool, 
        unique: bool, 
        hidden: bool, 
        normalize: Callable[[str], str],
        tree: TreeT[str]
    ):
        self.tree = tree_.Tree(tree, normalize)

        super().__init__(
            context, 
            name, 
            alias, 
            required, 
            unique, 
            hidden
        )



class AttributePerson(Attribute[Person]):
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
            unique_in_list=unique,
            interactability=hidden 
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
            unique_in_list=unique,
            interactability=hidden
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

def get(context: ContextT, attr: str) -> Attribute:
    try:
        lookup = _ATTR_LOOKUP[context]
    except KeyError:
        raise fbe.TemporaryFeedbackError
    
    try:
        return lookup[attr]
    except KeyError:
        raise fbe.InvalidAttribute(attr)

def get_all(context: ContextT) -> tuple[Attribute, ...]:
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
                "Broodal Fight 1": {
                    "test3": {
                        "test2": {}
                    }
                }
            },
        }
    )
    # attr = AttributePluralStr(TMP_CTX, "test", ["test"], True, True, True, 10, 100)
    # print(attr._from_str(f'[""]'))



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