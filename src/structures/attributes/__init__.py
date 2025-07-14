from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
import decimal
import enum
import functools
import json
import pickle
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator, NamedTuple, Protocol, Self, TypeAliasType, TypedDict, Union, overload
import typing

from database import dbutils, layout, queries
import errors
from errors.feedback import feedbacks
from structures.attributes import slot_type
from structures.attributes import collection
from structures.attributes.slot_type import LiteralToStrPossibleT, SlotTypeT
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from utils import numbers, text
if TYPE_CHECKING:
    from structures.attributes.static_attribute import StaticAttribute
    from structures.attributes.task_attribute import TaskAttribute
    from structures.attributes.user_attribute import UserAttribute



type AnyAttributeT[T: SlotTypeT] = StaticAttribute[T] | TaskAttribute[T] | UserAttribute[T]
ANY_ATTRIBUTE = (StaticAttribute, TaskAttribute, UserAttribute)

type UniquenessAttributeT[T: SlotTypeT] = UserAttribute[T]
UNIQUENESS_ATTRIBUTE = (UserAttribute,)

type UniquenessExtendedAttributeT[T: SlotTypeT] = StaticAttribute[T] | TaskAttribute[T]
UNIQUENESS_EXTENDED_ATTRIBUTE = (StaticAttribute, TaskAttribute)

type CollectionAttributeT[T: SlotTypeT] = TaskAttribute[T] | UserAttribute[T]
COLLECTION_ATTRIBUTE = (TaskAttribute, UserAttribute)


@functools.total_ordering
class Uniqueness:
    _value_mapping: dict[int, Self] = {}
    _name_mapping: dict[str, Self] = {}

    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value

        if self.value in self.__class__._value_mapping:
            raise RuntimeError
        
        if self.name in self.__class__._name_mapping:
            raise RuntimeError
        
        self.__class__._value_mapping[value] = self
        self.__class__._name_mapping[name] = self

    @classmethod
    def _init_cls(cls):
        cls.NONE = cls('none', 0)
        cls.PER_VALUE = cls('per_value', 1)

        for subcls in cls.__subclasses__():
            subcls._value_mapping = cls._value_mapping.copy()
            subcls._name_mapping = cls._name_mapping.copy()
            subcls._init_cls()
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Uniqueness) and self.value == other.value:
            return True
        
        return NotImplemented
    
    def __lt__(self, other: Any):
        if isinstance(other, Uniqueness):
            return self.value < other.value
        
        return NotImplemented
    
    def __bool__(self) -> bool:
        return bool(self.value)
    
    @classmethod
    def get_by_value(cls, value: int) -> Self:
        return cls._value_mapping[value]
    
    @classmethod
    def get_by_name(cls, name: str) -> Self:
        return cls._name_mapping[name]
    

@functools.total_ordering
class UniquenessExtended(Uniqueness):
    @classmethod
    def _init_cls(cls):
        cls._value_mapping = cls._value_mapping.copy()
        cls._name_mapping = cls._name_mapping.copy()

        cls.PER_LIST = cls('per_list', 2)

Uniqueness._init_cls()


UniquenessEnum: enum.Enum = enum.Enum(
    'UniquenessEnum', [(obj.name, obj) for obj in Uniqueness._value_mapping.values()]
)

UniquenessExtendedEnum = enum.Enum(
    'UniquenessEnum', [(obj.name, obj) for obj in UniquenessExtended._value_mapping.values()]
)

@dataclass
class AttributeDataCache[T: SlotTypeT]():
    aliases: frozenset[str] | None = None
    collection: Collection[T] | None = None


type RawCollectionNodesT[T: SlotTypeT] = frozenset[RawCollectionNode[T]]

class RawCollectionNode[T: SlotTypeT](NamedTuple):
    value: T
    aliases: frozenset[T]
    sort_value: int
    children: RawCollectionNodesT[T]

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



def set_collection_helper[T: SlotTypeT](
    top_raw_nodes: RawCollectionNodesT[T], 
    attribute: CollectionAttributeT
) -> 'Collection[T]':
    if not top_raw_nodes:
        return Collection(
            attribute=attribute,
            top_nodes=frozenset(),
            normed_syn_to_node=MappingProxyType({})
        )
    
    normed_to_node: dict[T, CollectionNode[T]] = {}
    node_count: int = 0

    def recursively_create_children(parent: None | CollectionNode[T], raw_node: RawCollectionNode[T], depth: int) -> CollectionNode[T]:
        if depth > collection.MAX_DEPTH:
            raise feedbacks.temp("Max collection depth exceeded")

        nonlocal node_count
        node_count += 1

        if node_count > collection.MAX_ELEMS:
            raise feedbacks.temp("Max amount of collection elems surpassed!")
        
        if not numbers.is_int32(raw_node.sort_value):
            raise feedbacks.temp("Sort value out of range")
        
        normed_value: T = attribute.slot_type.norm(raw_node.value)
        aliases: set[T] = set(map(attribute.slot_type.norm, raw_node.aliases))

        if normed_value in aliases:
            aliases.remove(normed_value)
        
        node = CollectionNode(
            value=raw_node.value,
            aliases=frozenset(aliases),
            sort_value=raw_node.sort_value,
            children=frozenset(),
            parent=parent,
            slot_type=attribute.slot_type
        )

        depth += 1
        
        node._post_set_children(frozenset(
            recursively_create_children(node, child, depth) 
            for child in 
            raw_node.children
        ))

        for normed_syn in (normed_value, *node.aliases):
            if normed_syn in normed_to_node:
                raise feedbacks.temp("Same syn appeared twice")
            
            normed_to_node[normed_syn] = node
        
        return node
    
    top_nodes = frozenset(recursively_create_children(None, raw_node, 1) for raw_node in top_raw_nodes)

    TblNodes = dbutils.get_attribute_collection_node_table(type(attribute))
    TblAliases = dbutils.get_attribute_collection_node_alias_table(type(attribute))
    
    def recursively_insert_children(parent_id: int | None, nodes: CollectionNodesT[T]) -> None:
        if not nodes:
            return
        
        for node in nodes:
            cursor.execute(f"""
                INSERT INTO {TblNodes} (
                    {TblNodes._attribute_id},
                    {TblNodes.value},
                    {TblNodes.sort_value},
                    {TblNodes.parent_id}
                ) 
                VALUES (
                    {h|attribute.id},
                    {h|pickle.dumps(node.value)},
                    {h|node.sort_value},
                    {h|parent_id}
                )
            """, h.steal())

            node_id: int = cursor.lastrowid  # type: ignore

            if node.aliases:
                cursor.execute(f"""
                    INSERT INTO {TblAliases} (
                        {TblAliases._attribute_id},
                        {TblAliases._attribute_collection_node_id},
                        {TblAliases.alias}
                    )
                    VALUES 
                        {','.join(f"""(
                            {h|attribute.id},
                            {h|node_id},
                            {h|pickle.dumps(alias)}
                        )""" for alias in node.aliases)}
                """, h.steal())

            recursively_insert_children(node_id, node.children)

    h = queries.ArgHelper()

    with queries.connected() as (_, cursor), attribute.locked:
        # We go from top nodes down the tree so we can be sure
        # the parent_id is already inserted and the foreign key
        # check succeeds
        recursively_insert_children(None, top_nodes)

    return Collection(
        attribute=attribute,
        top_nodes=top_nodes,
        normed_syn_to_node=MappingProxyType(normed_to_node)
    )

def get_collection_helper[T: SlotTypeT](attribute: CollectionAttributeT[T]) -> Collection[T]:
    h = queries.ArgHelper()
    ALIASES_KEY: str = 'aliases'

    TblNode = dbutils.get_attribute_collection_node_table(type(attribute))
    TblNodeAlias = dbutils.get_attribute_collection_node_alias_table(type(attribute))

    with queries.connected() as (conn, cursor):
        cursor.execute(f"""
            SELECT *
            FROM {TblNode}
            WHERE {TblNode._attribute_id} = {h|attribute.id}
        """, h.steal())

        result = queries.Rows(cursor.fetchall(), TblNode)

        cursor.execute(f"""
            SELECT 
                {TblNodeAlias._attribute_collection_node_id},
                {TblNodeAlias.alias}
            FROM
                {TblNodeAlias}
            WHERE
                {TblNodeAlias._attribute_id} = {h|attribute.id}
        """, h.steal())

        aliases_result: queries.ManyRowsT = cursor.fetchall()

    row_id_to_row: dict[int, queries.OneRowT] = {row[TblNode.id]: row for row in result}
    row_id_to_child_row_ids: dict[int, list[int]] = {}

    top_rows: queries.ManyRowsT = []
    
    for row in result:
        row_id_to_child_row_ids \
            .setdefault(row[TblNode.parent_id], []) \
            .append(row[TblNode.id])
        
        if row[TblNode.parent_id] is None:
            top_rows.append(row)
    
        row[TblNode.value] = pickle.loads(row[TblNode.value])
        row[ALIASES_KEY] = []

    for alias_row in aliases_result:
        row = row_id_to_row[alias_row[TblNodeAlias._attribute_collection_node_id]]
        alias = pickle.loads(alias_row[TblNodeAlias.alias])

        row[ALIASES_KEY].append(alias)

    del TblNodeAlias

    normed_syn_to_node: dict[T, CollectionNode[T]] = {}

    def recursively_create_children(parent: CollectionNode[T] | None, row: queries.OneRowT) -> CollectionNode[T]:
        node = CollectionNode(
            value=row[TblNode.value],
            aliases=frozenset(row[ALIASES_KEY]),
            sort_value=row[TblNode.sort_value],
            children=frozenset(),
            parent=parent,
            slot_type=attribute.slot_type
        )

        children_ids = row_id_to_child_row_ids.get(row[TblNode.id], [])

        if children_ids:
            node._post_set_children(frozenset(
                recursively_create_children(node, row_id_to_row[child_id])
                for child_id in children_ids
            ))

        for syn in (node.value, *node.aliases):
            normed_syn_to_node[attribute.slot_type.norm(syn)] = node

        return node

    top_nodes = frozenset(recursively_create_children(None, row) for row in top_rows)
        
    return Collection(
        attribute=attribute,
        top_nodes=top_nodes,
        normed_syn_to_node=MappingProxyType(normed_syn_to_node)
    )