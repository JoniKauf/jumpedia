

import ast
from collections import Counter, defaultdict
from trickjump.context import Context
from datetime import datetime, time, timedelta
import functools
import json
import sys
from threading import Lock
from typing import Any, Callable, Hashable, Iterable, Literal, Optional as Opt, Self, Sequence, TypeVar, cast
from enum import Enum, auto
from discordtools import feedbackerrors as fbe
from people.person import Person
import re
from collections2 import tree
from trickjump.community import Community
import builtins
from collections2.range import Range

type AttrT = 'Attribute'
type AttributeValueTypeT = bool | int | float | str | time | datetime | timedelta


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


class ValueCollectionType(Enum):
    NONE = auto()
    LIST = auto()
    TREE = auto()

#------#   Attribute   #------#	

class Attribute[T: AttributeValueTypeT]:
    TYPE_ID: int
    MAX_SYN_LEN = 32
    MAX_ATTRIBUTES_PER_COMMUNITY = 50
    
    LOOKUP: dict[Community, dict[str, 'Attribute']] = {}

    # int | float
    NUMBER_MIN: int = -(2 ** 64)
    NUMBER_MAX: int = 2 ** 64 - 1
    NUMBER_MAX_LEN_AS_STR: int = len(str(NUMBER_MAX)) 

    # str
    STR_MAX_LEN = 1024

    # Collection
    COLLECTION_MAX_MEMORY = 1024 * 32
    COLLECTION_MAX_ELEMS = 1024

    MAX_DEPTH = 64

    LOCK = Lock()

    def __init__(
        self, 
        community: Community,
        name: str,
        alias: Iterable[str],
        value_type: type[T],
        value_collection: None | Sequence[tuple[T, int]] | tree.TreeT[tuple[T, int]],
        min_value_slots: int,
        max_value_slots: int,
        unique_slots: bool,
        unique_values_per_list: bool,
        user_bound: bool
    ):
        with self.__class__.LOCK:
            self.community = community

            self.name = self._normalize_and_validate_syn(name)
            self.alias = set(self._normalize_and_validate_syn(a) for a in alias)

            if self.value_type not in AttributeValueTypeT.__value__.__args__:
                raise TypeError
            
            self.value_type = value_type

            self.list: Opt[None | list[T]] = None
            self.tree: Opt[tree.Tree] = None

            self.sort_value: dict[T, int] = {}
            self.unnormalize = {}

            if not value_collection:
                pass
            elif isinstance(value_collection, Sequence):
                self.list = []

                for value in value_collection:
                    v_norm = self._normalize_and_implement(value)
                    self.list.append(v_norm)
                    
                if len(self.list) > self.COLLECTION_MAX_ELEMS:
                    raise fbe.TemporaryFeedbackError
                
                if sum(self.value_to_memory(v) for v in self.list) > self.COLLECTION_MAX_MEMORY:
                    raise fbe.TemporaryFeedbackError
            else:
                try:
                    self.tree = tree.Tree(
                        value_collection, 
                        self._normalize_and_implement, 
                        self.MAX_DEPTH, 
                        self.COLLECTION_MAX_ELEMS, 
                        self.NUMBER_MAX
                    )
                except tree.TreeError as e:
                    raise fbe.TemporaryFeedbackError(e)
                
                if sum(
                    self.value_to_memory(n.value) 
                    for n in self.tree._node_lookup.values()
                ) > self.COLLECTION_MAX_MEMORY:
                    raise fbe.TemporaryFeedbackError

            if min_value_slots < 0:
                raise fbe.TemporaryFeedbackError
            
            if max_value_slots < 1 or max_value_slots < min_value_slots:
                raise fbe.TemporaryFeedbackError
            
            self.min_value_slots = min_value_slots
            self.max_value_slots = max_value_slots

            self.unique_slots = unique_slots

            if unique_values_per_list and user_bound:
                raise fbe.TemporaryFeedbackError("dont work together")
            
            self.unique_value_per_list = unique_values_per_list
            self.user_bound = user_bound

            lookup = self.LOOKUP.setdefault(community, {})

            for syn in (name, *alias):
                lookup[syn] = self
                
            # TODO:
            # - Add to database

    def _normalize_and_validate_syn(self, syn: str) -> str:
        syn = re.sub(_DUPLICATE_WHITESPACE_PATTERN, '_', syn.strip().casefold())

        if not syn:
            raise fbe.TemporaryFeedbackError
        
        if len(syn) > self.MAX_SYN_LEN:
            raise fbe.TemporaryFeedbackError
        
        if syn in self.LOOKUP.setdefault(self.community, {}):
            raise fbe.TemporaryFeedbackError
        
        illegal_chars: set[str] = set()

        for char in syn:
            if char not in _VALID_CHARS:
                illegal_chars.add(char)

        if illegal_chars:
            raise fbe.TemporaryFeedbackError(illegal_chars)
        
        return syn
    
    def _normalize_and_implement(self, value: tuple[T, int]) -> T:
        unnormalized, sort_value = value

        if isinstance(value, self.value_type):
            raise TypeError
        
        normalized = self.normalize(unnormalized)

        self.sort_value[normalized] = sort_value
        
        prev_unnormalized = self.unnormalize.get(normalized, None)

        if prev_unnormalized is None:
            self.unnormalize[normalized] = unnormalized
        else: 
            raise fbe.TemporaryFeedbackError()
        
        return normalized
    
    def normalize(self, unnormalized: T) -> T:
        if isinstance(unnormalized, str):
            normalized: T = re.sub(_DUPLICATE_WHITESPACE_PATTERN, " ", unnormalized.strip().casefold())  # type: ignore
        else:
            normalized = unnormalized
        
        return normalized
    
    def value_to_memory(self, value: T) -> int:
        if isinstance(value, str):
            return len(value)
        if isinstance(value, int):
            return 8
        if isinstance(value, float):
            return 8
        if isinstance(value, time):
            return 4
        if isinstance(value, datetime):
            return 8
        if isinstance(value, timedelta):
            return 8
        
        raise TypeError

    def is_empty(self, value: Opt[str]) -> bool:
        return self._from_str(value) is None
            
    def _from_str(self, value: Opt[str]) -> Opt[T]:
        if value is None or not (value := value.strip()):
            return None
        
        try:
            json.loads
        except json.JSONDecodeError:
            #todo
        
        results: list[T]
        match self.value_type:
            case builtins.bool:
                value = value.lower()

                if value == "false":
                    res = False
                elif value == "true":
                    res = True
                else:
                    raise fbe.NotAProperValue("boolean", value)
            case builtins.int | builtins.float:
                if len(value) > self.__class__.NUMBER_MAX_LEN_AS_STR:
                    raise fbe.OutsideOfValidRange(value, self.__class__.NUMBER_MIN, self.__class__.NUMBER_MAX )

                try:
                    res = self.value_type(value)
                except ValueError:
                    raise fbe.NotAProperValue("number", value)

                if not (self.__class__.NUMBER_MIN < res < self.__class__.NUMBER_MAX):
                    raise fbe.OutsideOfValidRange(res, self.__class__.NUMBER_MIN, self.__class__.NUMBER_MAX)
            case builtins.str:
                if len(value) > self.__class__.STR_MAX_LEN:
                    raise fbe.TooLongValue("string", value, self.__class__.STR_MAX_LEN)
                
                res = re.sub(_DUPLICATE_WHITESPACE_PATTERN, " ", value)
            case _:
                raise ValueError

        return res  # type: ignore
            
    
            
    
            
        
    

# #------#   Attribute Specific Implementations   #------#

# class AttributeBool(Attribute[bool]):
#     TYPE_ID = 1

#     def _from_str(self, value: Opt[str]) -> Opt[bool]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         value = value.lower()

#         if value == "true":
#             return True
#         if value == "false":
#             return False
        
#         raise fbe.NotAProperValue("boolean", value)
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return 2 * sign
        
#         return (not v) * sign
    

# class AttributeInt(Attribute[int]):
#     TYPE_ID = 2

    

#     def _from_str(self, value: Opt[str]) -> Opt[int]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         if len(value) > self.__class__.NUMBER_MAX_LEN_AS_STR:
#             raise fbe.OutsideOfValidRange(
#                 value, self.__class__.NUMBER_MIN, self.__class__.NUMBER_MAX
#             )
        
#         try:
#             result = int(value)
#         except ValueError:
#             raise fbe.NotAProperValue("integer", value)

#         if not (self.__class__.NUMBER_MIN < result < self.__class__.NUMBER_MAX):
#             raise fbe.OutsideOfValidRange(
#                 result, self.__class__.NUMBER_MIN, self.__class__.NUMBER_MAX
#             )
        
#         return result

#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             v = self.NUMBER_MAX + 1
            
#         return v * sign
    

# class AttributeStr(Attribute[str]):
#     TYPE_ID = 3

#     MAX_STR_LEN = 2 ** 10

#     def _from_str(self, value: Opt[str]) -> Opt[str]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         if len(value) > self.__class__.MAX_STR_LEN:
#             raise fbe.TooLongValue("string", value, self.__class__.MAX_STR_LEN)
        
#         return value

#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return ((sys.maxunicode + 1) * sign,)
        
#         if not case_sensitive:
#             v = v.casefold()

#         return tuple(ord(char) * sign for char in v)


# class AttributeStrCollection(AttributeStr):
#     TYPE_ID = 4

#     MAX_COLLECTION_LEN = 2 ** 12

#     def __init__(
#         self, 
#         context: ContextT,
#         name: str, 
#         alias: Iterable[str], 
#         required: bool,
#         unique: bool,
#         hidden: bool, 
#         *args: *tuple[Sequence[str]]
#     ):
#         collection, = args             

#         super().__init__(
#             context=context,
#             name=name, 
#             alias=alias, 
#             required=required,
#             unique_in_list=unique,
#             interactability=hidden
#         )

#         # dict[casefolded_val, tuple[val, index]]
#         self._collection: dict[str, tuple[str, int]] = {}

#         if len(collection) > self.__class__.MAX_COLLECTION_LEN:
#             raise fbe.TooManyCollectionElements(
#                 self.name, self.__class__.MAX_COLLECTION_LEN
#             )
        
#         for i, elem in enumerate(collection):
#             elem = elem.strip()
#             elem_cf = elem.casefold()
            
#             if elem_cf in collection:
#                 raise fbe.CollectionElementCollision(self.name, elem_cf)
            
#             self._collection[elem_cf] = (elem, i)

#     @property
#     def collection(self) -> dict[str, tuple[str, int]]:
#         return self._collection
    
#     def _from_str(self, value: Opt[str]) -> Opt[str]:
#         v = super()._from_str(value)

#         if v is None:
#             return None
        
#         if v not in self.collection:
#             raise fbe.NotPartOfTheCollection(self.name, v)
        
#         return v.casefold()
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return len(self.collection) * sign
        
#         return self.collection[v][1] * sign
    
# class AttributeStrCollectionTree(Attribute[str]):
#     def __init__(
#         self, 
#         context: str, 
#         name: str, 
#         alias: Iterable[str], 
#         required: bool, 
#         unique: bool, 
#         hidden: bool, 
#         normalize: Callable[[str], str],
#         tree: TreeT[str]
#     ):
#         self.tree = tree_.Tree(tree, normalize)

#         super().__init__(
#             context, 
#             name, 
#             alias, 
#             required, 
#             unique, 
#             hidden
#         )



# class AttributePerson(Attribute[Person]):
#     TYPE_ID = 5
#     MAX_PERSON_NAME_LEN = Person.MAX_PERSON_NAME_LEN

#     def _from_str(self, value: Opt[str]) -> Opt[Person]:
#         if value is None or not (value := value.strip()):
#             return None
        
#         return Person.get(value)
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return ((sys.maxunicode + 1) * sign,)
        
#         name: str = v.name if case_sensitive else v.name.casefold()

#         return tuple(ord(char) * sign for char in name)


# #------#   Attribute Plural Implementations   #------#

# ATTRIBUTE_PLURAL_BASE_ID = 128

# class AttributePluralStr(AttributeStr, _AttributePluralMixin[str]):
#     TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributeStr.TYPE_ID

#     def __init__(
#         self, 
#         context: ContextT,
#         name: str, 
#         alias: Iterable[str], 
#         required: bool,
#         unique: bool,
#         hidden: bool, 
#         *other: *tuple[int, int]
#     ):
#         max, max_duplicates = other

#         super().__init__(
#             context=context,
#             name=name, 
#             alias=alias, 
#             required=required,
#             unique_in_list=unique,
#             interactability=hidden 
#         )

#         _AttributePluralMixin.__init__(
#             self,
#             max=max,
#             max_duplicates=max_duplicates
#         )
    
#     _from_str: Callable[[Opt[str]], Opt[list[str]]] = _get_plural_from_str_method(AttributeStr._from_str)  # type: ignore
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return (((sys.maxunicode + 1) * sign,),)
        
#         return tuple(
#             tuple(ord(char) * sign for char in (
#                 s if case_sensitive else s.casefold()
#             )) 
#             for s in v
#         )

# class AttributePluralStrCollection(AttributeStrCollection, _AttributePluralMixin[str]):
#     TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributeStrCollection.TYPE_ID

#     def __init__(
#         self, 
#         context: ContextT,
#         name: str, 
#         alias: Iterable[str], 
#         required: bool, 
#         unique: bool,
#         hidden: bool,
#         *other: *tuple[int, int, Sequence[str]]
#     ):
#         max, max_duplicates, collection = other

#         super().__init__(
#             context,
#             name,
#             alias,
#             required,
#             unique,
#             hidden,
#             *(collection,)
#         )

#         _AttributePluralMixin.__init__(
#             self, 
#             max=max,
#             max_duplicates=max_duplicates
#         )

#     _from_str: Callable[[Opt[str]], Opt[list[str]]] = _get_plural_from_str_method(AttributeStrCollection._from_str)  # type: ignore
    
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return (len(self.collection) * sign,)
        
#         return tuple(
#             self.collection[elem][1] for elem in v
#         )
    

# class AttributePluralPerson(AttributePerson, _AttributePluralMixin[Person]):
#     TYPE_ID = ATTRIBUTE_PLURAL_BASE_ID + AttributePerson.TYPE_ID
    
#     def __init__(
#         self, 
#         context: ContextT, 
#         name: str, 
#         alias: Iterable[str], 
#         required: bool,
#         unique: bool,
#         hidden: bool,
#         *other: *tuple[int, int]
#     ):
#         max, max_duplicates = other

#         super().__init__(
#             context=context, 
#             name=name, 
#             alias=alias, 
#             required=required,
#             unique_in_list=unique,
#             interactability=hidden
#         )

#         _AttributePluralMixin.__init__(
#             self, 
#             max=max,
#             max_duplicates=max_duplicates
#         )

#     _from_str: Callable[[Opt[str]], Opt[list[Person]]] = _get_plural_from_str_method(AttributePerson._from_str)  # type: ignore
     
#     def sort_key(self, value: Opt[str], sign: Literal[+1, -1], case_sensitive: bool):
#         v = self._from_str(value)

#         if v is None:
#             return (((sys.maxunicode + 1) * sign,),)
        
#         return tuple(
#             tuple(ord(char) * sign for char in (
#                 person.name if case_sensitive else person.name.casefold()
#             )) 
#             for person in v
#         )


#------#   Module Functionality   #------#

def get(context: Context, attr: str) -> Attribute:
    try:
        lookup = Attribute.LOOKUP[context.community]
    except KeyError:
        raise fbe.TemporaryFeedbackError
    
    try:
        return lookup[attr]
    except KeyError:
        raise fbe.InvalidAttribute(attr)

def get_all(context: Context) -> tuple[Attribute, ...]:
    return tuple(Attribute.LOOKUP[context.community].values())
    

if __name__ == '__main__':
    def debug_print(attr: Attribute):
        print("\n\n" + "\n".join(f"{k} = {v!r}" for k, v in attr.__dict__.items() if not k.startswith("__")))
    
    attr_name = Attribute(Community(), "difficulty", ["diff", "d"], str, [("0/10", 0), ("0.5/10", 1), ("1/10", 2)], 0, 1, True, True, False)
    attr_count = Attribute(Community(), "count", ["c"], int, [(1, 1), (2, 2), (3, 3)], 1, 1, True, True, False)
    debug_print(attr_name)
    debug_print(attr_count)
    
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