from abc import abstractmethod
import builtins
from dataclasses import dataclass, field
import datetime as dt
from decimal import Decimal
import decimal
import enum
import itertools
import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Literal, NamedTuple, Self, assert_never, final, overload
import typing

from database import queries, typed
from database.simple_orm import Arg, Rows
from discordtools import messaging
from errors.feedback import feedbacks
from structures.attributes import slot_type
from structures.attributes import collection
from structures.attributes.slot_type import LiteralToStrPossibleT, SlotType, SlotTypeT
from structures.attributes.collection import MAX_DEPTH, MAX_ELEMS, Collection, CollectionNode, CollectionNodesT
from structures.base_structure import BaseStructure
from structures.list import List
from utils import numbers, parsetools, text
if TYPE_CHECKING:
    from structures.attributes.static_attribute import StaticAttribute
    from structures.attributes.task_attribute import TaskAttribute
    from structures.attributes.user_attribute import UserAttribute



type AnyAttributeT[T: SlotTypeT] = StaticAttribute[T] | TaskAttribute[T] | UserAttribute[T]
ANY_ATTRIBUTE = (StaticAttribute, TaskAttribute, UserAttribute)

class Uniqueness(enum.IntEnum):
    NONE = 0
    PER_VALUE = 1
    PER_ATTRIBUTE = 2

    @classmethod
    def get(cls, v: int) -> 'Uniqueness': 
        return tuple(Uniqueness._member_map_.values())[v]  # type: ignore



type RawCollectionNodesT = frozenset[RawCollectionNode]

class RawCollectionNode(NamedTuple):
    slot: str
    aliases: frozenset[str]
    sort_value: int
    children: RawCollectionNodesT

# General
MIN_SYN_LEN: Final[int] = 1
MAX_SYN_LEN: Final[int] = 32
MAX_ALIAS_COUNT: Final[int] = 32
MAX_COLLECTION_ALIASES: Final[int] = 7
MAX_SLOTS: Final[int] = 32
SORT_KEY_NONE_NUMBER: Final[int] = max(abs(slot_type.NUMBER_MIN), abs(slot_type.NUMBER_MAX)) + 1


# Any of TYPES_LITERAL_ALLOWED or a list of any of TYPES_LITERAL_ALLOWED
type AttributeValueParseTypesT = LiteralToStrPossibleT | list[LiteralToStrPossibleT]
ATTRIBUTE_VALUE_PARSE_TYPES = (bool, int, str, [bool, int, str])

# Checking ATTRIBUTE_VALUE_PARSE_TYPES is too much effort and hard to generalize
# Just make sure it stays consistent when changing one



@dataclass(frozen=True)
class AttributeTables:
    attribute: type[typed.BaseAttribute]
    attribute_alias: type[typed.BaseAttributeAlias]


@dataclass(frozen=True)
class BaseNonStaticAttributeTables(AttributeTables):
    attribute_collection_node: type[typed.BaseAttributeCollectionNode]
    attribute_collection_node_alias: type[typed.BaseAttributeCollectionNodeAlias]
    attribute_task_value: type[typed.BaseAttributeTaskValue]
    
    def __post_init__(self) -> None:
        if self.__class__ == BaseNonStaticAttributeTables:
            raise RuntimeError
        

@dataclass(frozen=True, kw_only=True)
class BaseAttribute[T: SlotTypeT](BaseStructure):
    __structure_name__ = "base attribute"
    tables: ClassVar[AttributeTables]
    allow_min_slots_on_creation: ClassVar[bool] = False
    deletable: ClassVar[bool] = True

    list: 'List'
    id: int 
    name: str
    slot_type: SlotType[T]
    position: int
    min_slots: int
    max_slots: int

    value_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=1,
        strict_type=ATTRIBUTE_VALUE_PARSE_TYPES
    )

    @property
    def identity(self) -> tuple[int, ...]:
        return (ANY_ATTRIBUTE.index(self.__class__), self.id) + self.list.identity
    
    @property
    def required(self) -> bool:
        return self.min_slots > 0
    
    # --- Methods ---

    def __post_init__(self) -> None:
        if self.__class__ == BaseAttribute:
            raise RuntimeError()

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    def get_syns(self) -> set[str]:
        return {self.name} | self.get_aliases()
    
    def get_aliases(self) -> frozenset[str]:
        TblAlias = self.__class__.tables.attribute_alias

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {TblAlias.real_alias}
                FROM {TblAlias}
                WHERE {TblAlias.attribute_id} = {arg(self.id)}
            """)

            rows = c.fetchall(TblAlias)
        
        return frozenset(row.real_alias for row in rows)
    
    def get_collection(self) -> Collection[T]:
        return Collection(
            attribute=self,
            top_nodes=frozenset(),
            normalized_to_node=MappingProxyType({})
        )

    def value_from_loaded(self, loaded: AttributeValueParseTypesT) -> builtins.list[T]:
        if not isinstance(loaded, list):
            loaded = [loaded]

        if not (self.min_slots <= (count := len(loaded)) <= self.max_slots):
            raise feedbacks.temp("Count of values not between limits", min=self.min_slots, count=count, max=self.max_slots)
        
        result_values: list[T] = []
        
        for slot in loaded:
            if not isinstance(slot, self.slot_type.type):
                raise feedbacks.temp(f"not list, str or value type '{loaded}'")
            
            if not self.slot_type.literal_to_str_possible:
                raise feedbacks.temp(f"value type '{self.slot_type}' is not valid")
            
            parsed_value = self.slot_type.from_raw_str(str(slot))

            result_values.append(parsed_value)
        
        return result_values

    def value_from_str(self, s: str) -> Any:
        return self.value_from_loaded(self.__class__.value_parser.loads(s))
    

    type ValueSortKeyT = tuple[SlotType.SortKeyT, *tuple[SlotType.SortKeyT, ...]]

    def sort_key(self, v: builtins.list[T], sign: Literal[+1, -1]) -> tuple[ValueSortKeyT, *tuple[ValueSortKeyT, ...]]:        
        if not v:
            return ((SORT_KEY_NONE_NUMBER * sign,),)
        
        if isinstance(self, BaseNonStaticAttribute):
            collection = self.get_collection()
            
            if not collection.is_empty:
                result: list[int] = []

                for slot in v:
                    node = collection.get_node_by_syn(slot)

                    if node is None:
                        raise ValueError
                    
                    result.append(node.sort_value * sign)
                
                return (tuple(result),)  # type: ignore
                
        return tuple(
            self.slot_type.sort_key(slot, sign)
            for slot in v
        )  # type: ignore


class BaseNonStaticAttribute[T: SlotTypeT](BaseAttribute[T]):
    tables: ClassVar[BaseNonStaticAttributeTables]

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.__class__ == BaseNonStaticAttribute:
            raise RuntimeError
    

    def value_from_loaded(self, loaded: AttributeValueParseTypesT) -> builtins.list[T]:
        value = super().value_from_loaded(loaded)
        
        collection = self.get_collection()

        if collection.is_empty:
            return value
        
        result: list[T] = []

        for slot in value:
            node = collection.get_node_by_syn(slot)

            if node is None:
                raise feedbacks.temp("Collection node not found")
            
            result.append(node.slot)

        return result


    def get_collection(self) -> Collection[T]:
        TblNode = self.__class__.tables.attribute_collection_node
        TblNodeAlias = self.__class__.tables.attribute_collection_node_alias

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {TblNode}
                WHERE {TblNode.attribute_id} = {arg(self.id)}
            """)

            result = c.fetchall(TblNode)

            c.execute(lambda arg: t"""
                SELECT 
                    {TblNodeAlias.alias}
                FROM
                    {TblNodeAlias}
                WHERE
                    {TblNodeAlias.attribute_id} = {arg(self.id)}
            """)

            aliases_result = c.fetchall(TblNodeAlias)

        del TblNodeAlias

        row_id_to_row = {row.id: row for row in result}
        row_id_to_child_row_ids: dict[int | None, list[int]] = {}

        top_rows: list[typed.BaseAttributeCollectionNode] = []
        row_id_to_aliases: dict[int, list[T]] = {}

        for row in result:
            row_id_to_child_row_ids \
                .setdefault(row.parent_id, []) \
                .append(row.id)
            
            if row.parent_id is None:
                top_rows.append(row)
        
            row_id_to_aliases[row.id] = []

        for alias_row in aliases_result:
            row = row_id_to_row[alias_row.attribute_collection_node_id]
            row_id_to_aliases[row.id].append(self.slot_type.from_clean_str(alias_row.alias))

        normed_to_node: dict[T, CollectionNode[T]] = {}

        def recursively_create_children(parent: CollectionNode[T] | None, row: typed.BaseAttributeCollectionNode) -> CollectionNode[T]:
            node = CollectionNode(
                slot=self.slot_type.from_clean_str(row.slot),
                aliases=frozenset(row_id_to_aliases[row.id]),
                sort_value=row.sort_value,
                children=frozenset(),
                parent=parent
            )

            normed_to_node.update({
                self.slot_type.norm(syn): node
                for syn in 
                (node.slot, *node.aliases)
            })

            children_ids = row_id_to_child_row_ids.get(row.id, [])

            if children_ids:
                node._post_set_children(frozenset(
                    recursively_create_children(node, row_id_to_row[child_id])
                    for child_id in children_ids
                ))

            return node

        top_nodes = frozenset(recursively_create_children(None, row) for row in top_rows)
            
        return Collection(
            attribute=self,
            top_nodes=top_nodes,
            normalized_to_node=MappingProxyType(normed_to_node)
        )
    
    def set_collection(
        self,
        top_raw_nodes: RawCollectionNodesT, 
    ) -> 'Collection[T]':
        TblNodes = self.__class__.tables.attribute_collection_node
        TblAliases = self.__class__.tables.attribute_collection_node_alias
        
        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {TblNodes}
                WHERE {TblNodes.attribute_id} = {arg(self.id)}
            """)

            if not top_raw_nodes:
                return Collection(
                    attribute=self,
                    top_nodes=frozenset(),
                    normalized_to_node=MappingProxyType({})
                )
            
            norm_to_node: dict[T, CollectionNode[T]] = {}
            node_count: int = 0

            def recursively_create_children(parent: None | CollectionNode[T], raw_node: RawCollectionNode, depth: int) -> CollectionNode[T]:
                # Check depth
                if depth > MAX_DEPTH:
                    raise feedbacks.temp("Max collection depth exceeded")
                
                # Check total node count
                nonlocal node_count
                node_count += 1

                if node_count > MAX_ELEMS:
                    raise feedbacks.temp("Max amount of collection elems surpassed!")
                
                # Check valid sort_value
                if not numbers.is_int32(raw_node.sort_value):
                    raise feedbacks.temp("Sort value out of range")
                
                # Get and check slot and aliases
                real_slot = self.slot_type.from_raw_str(raw_node.slot)
                norm_slot = self.slot_type.norm(real_slot)
                norm_to_real_aliases: dict[T, T] = {}

                for raw_alias in raw_node.aliases:
                    real_alias = self.slot_type.from_raw_str(raw_alias)
                    norm_to_real_aliases[self.slot_type.norm(real_alias)] = real_alias

                # Remove alias if the name is in aliases
                norm_to_real_aliases.pop(norm_slot, None)

                if len(norm_to_real_aliases) > MAX_ALIAS_COUNT:
                    raise feedbacks.temp("Too many aliases")

                node = CollectionNode(
                    slot=real_slot,
                    aliases=frozenset(norm_to_real_aliases.values()),
                    sort_value=raw_node.sort_value,
                    children=frozenset(),
                    parent=parent
                )

                for normed_syn in (norm_slot, *norm_to_real_aliases):
                    if normed_syn in norm_to_node:
                        raise feedbacks.temp("Same syn appeared twice")
                    
                    norm_to_node[normed_syn] = node

                # Create and insert child nodes recursively
                child_nodes = frozenset(
                    recursively_create_children(node, child, depth + 1) 
                    for child in 
                    raw_node.children
                )

                node._post_set_children(child_nodes)

                # Return result
                return node
            
            top_nodes = frozenset(recursively_create_children(None, raw_node, 1) for raw_node in top_raw_nodes)
            
            def recursively_insert_children(parent_id: int | None, nodes: CollectionNodesT[T]) -> None:
                if not nodes:
                    return
                
                for node in nodes:
                    c.execute(lambda arg: t"""
                        INSERT INTO {TblNodes} (
                            {TblNodes.attribute_id},
                            {TblNodes.slot},
                            {TblNodes.sort_value},
                            {TblNodes.parent_id}
                        ) 
                        VALUES (
                            {arg(self.id)},
                            {arg(self.slot_type.to_str(node.slot))},
                            {arg(node.sort_value)},
                            {arg(parent_id)}
                        )
                    """)

                    node_id = c.last_generated_id

                    if node.aliases:
                        count = len(node.aliases)

                        c.executemany(lambda args: t"""
                            INSERT INTO {TblAliases} (
                                {TblAliases.attribute_id},
                                {TblAliases.attribute_collection_node_id},
                                {TblAliases.alias}
                            )
                            VALUES (
                                {args(itertools.repeat(self.id, count))},
                                {args(itertools.repeat(node_id, count))},
                                {args(map(self.slot_type.to_str, node.aliases))}
                            )    
                        """)

                    recursively_insert_children(node_id, node.children)

            # We go from top nodes down the tree so we can be sure
            # the parent_id is already inserted and the foreign key
            # check succeeds
            recursively_insert_children(None, top_nodes)

            return Collection(
                attribute=self,
                top_nodes=top_nodes,
                normalized_to_node=MappingProxyType(norm_to_node)
            )