from abc import abstractmethod
import builtins
from dataclasses import dataclass, field
import datetime as dt
from decimal import Decimal
import decimal
import enum
import functools
import json
import pickle
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, NamedTuple, Self, final, overload
import typing

from database import queries, typed
from discordtools import messaging
import errors
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



@dataclass(frozen=True)
class AttributeTables:
    attribute: type[typed.BaseAttribute]
    attribute_alias: type[typed.BaseAttributeAlias]


@dataclass(frozen=True)
class BaseNonStaticAttributeTables(AttributeTables):
    attribute_collection_node: type[typed.BaseCollectionAttributeCollectionNode]
    attribute_collection_node_alias: type[typed.BaseCollectionAttributeCollectionNodeAlias]
    attribute_task_value: tuple[
        type[typed.BaseAttributeTaskValue], 
        type[typed.BaseAttributeTaskValue], 
        type[typed.BaseAttributeTaskValue]
    ]
    
    def get_attribute_task_value_table(self, uniqueness: Uniqueness):
        return self.attribute_task_value[uniqueness.value]
    
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
    uniqueness: Uniqueness

    value_parser: ClassVar[parsetools.SafeJsonParser] = parsetools.SafeJsonParser(
        max_depth=collection.MAX_DEPTH,
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
            c.execute(lambda arg: f"""
                SELECT {TblAlias.alias}
                FROM {TblAlias}
                WHERE {TblAlias.attribute_id} = {arg(self.id)}
            """)

            rows = c.fetchall(TblAlias)
        
        return frozenset(row.alias for row in rows)
    
    def get_collection(self) -> Collection[T]:
        return Collection(
            attribute=self,
            top_nodes=frozenset(),
            normed_syn_to_node=MappingProxyType({})
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
        
        values = self._convert_slots_to_collection_slots(result_values)

        # Validate uniqueness
        normed_to_val: dict[T, T] = {}
        unique_slots: bool = self.uniqueness >= Uniqueness.PER_VALUE

        for v in values:
            normed_v = self.slot_type.norm(v)
            other_v = normed_to_val.get(normed_v, None)

            if other_v is None:
                normed_to_val[normed_v] = v
                continue
            
            if unique_slots:
                raise feedbacks.temp(f"For the attribute {self.name} the slots must be unique. The value {v} appeared multiple times.")

            if other_v != v:
                raise feedbacks.temp(f"All values that are equal case insensitively must be exactly equal. {other_v} != {v}")
        
        return values  

    def value_from_str(self, s: str) -> Any:
        return self.value_from_str(self.__class__.general_from_str(
            s, 
            self.__class__.value_parser
        ))

    @classmethod
    def general_from_str[T_: AttributeValueParseTypesT](cls, s: str, parser: parsetools.SafeJsonParser[T_]) -> T_:
        try:
            return parser.loads(s)
        except json.JSONDecodeError as e:
            raise feedbacks.temp(f"Not valid json at ...{e.msg[e.pos:e.pos + 10]}...")
        except RecursionError as e:
            raise feedbacks.temp(f"Max depth for json exceeded")
        except TypeError as e:
            raise feedbacks.temp(f"object {messaging.code(e.args[0])} is not of type {messaging.code(e.args[1])}")
        except Exception:
            raise feedbacks.temp("Unknown json parse exception")
        

    def to_str(self, obj: T) -> str:
        if isinstance(obj, (bool, int, Decimal, str)):
            return str(obj)
        
        if isinstance(obj, (dt.time, dt.date, dt.datetime)):
            return obj.isoformat()
        
        if isinstance(obj, (dt.timedelta)):
            return parsetools.unparse_timedelta(obj)
        
        raise TypeError("Invalid")

    def _convert_slots_to_collection_slots(self, value: builtins.list[T]) -> builtins.list[T]:
        collection = self.get_collection()

        if not collection.is_empty:
            return value
        
        result: list[T] = []
        
        for slot in value:
            node = collection.lookup_node(slot, None)
            
            if node is None:
                raise feedbacks.temp("Not part of the collection", slot)

            result.append(node.value)

        return result

    @classmethod
    def _sort_key_singular(cls, value: T, sign: Literal[+1, -1], slot_type: SlotType[T]) -> int:
        st: type[T] = slot_type.type

        if issubclass(st, bool):
            return int(value + 1) * sign  # type: ignore
            
        if issubclass(st, (int, Decimal)):
            return value * sign  # type: ignore

        if issubclass(st, dt.time):
            return (
                value.microsecond +           # type: ignore
                value.second *   1_000_000 +  # type: ignore
                value.minute *  60_000_000 +  # type: ignore
                value.hour * 3_600_000_000    # type: ignore
            ) * sign
        
        if issubclass(st, dt.datetime):
            return value.timestamp() * sign  # type: ignore
         
        if issubclass(st, dt.date):
            return value.timetuple().tm_yday * sign  # type: ignore
        
        if issubclass(st, dt.timedelta):
            return value.total_seconds() * sign  # type: ignore
        
        raise TypeError()
        
    def sort_key(self, v: builtins.list[T], sign: Literal[+1, -1]) -> tuple[int, ...]:        
        if not v:
            return (SORT_KEY_NONE_NUMBER + 1) * sign,
        
        collection = self.get_collection()

        if collection.is_empty:
            return tuple(
                self._sort_key_singular(value, sign, self.slot_type) 
                for value in v
            )

        return tuple((
                coll_item.sort_value
                if (coll_item := collection.lookup_node(slot, None)) is not None
                else SORT_KEY_NONE_NUMBER
            ) * sign
            for slot in v
        )
    

class BaseNonStaticAttribute[T: SlotTypeT](BaseAttribute[T]):
    tables: ClassVar[BaseNonStaticAttributeTables]

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.__class__ == BaseNonStaticAttribute:
            raise RuntimeError
    
    def get_collection(self) -> Collection[T]:
        TblNode = self.__class__.tables.attribute_collection_node
        TblNodeAlias = self.__class__.tables.attribute_collection_node_alias

        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {TblNode}
                WHERE {TblNode.attribute_id} = {arg(self.id)}
            """)

            result = c.fetchall(TblNode)

            c.execute(lambda arg: f"""
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
        row_id_to_child_row_ids: dict[int, list[int]] = {}

        top_rows: list[typed.BaseCollectionAttributeCollectionNode] = []
        row_id_to_aliases: dict[int, list[str]] = {}

        for row in result:
            row_id_to_child_row_ids \
                .setdefault(row.parent_id, []) \
                .append(row.id)
            
            if row.parent_id is None:
                top_rows.append(row)
        
            row_id_to_aliases[row.id] = []

        for alias_row in aliases_result:
            row = row_id_to_row[alias_row.attribute_collection_node_id]
            row_id_to_aliases[row.id].append(pickle.loads(alias_row.alias))

        normed_syn_to_node: dict[T, CollectionNode[T]] = {}

        def recursively_create_children(parent: CollectionNode[T] | None, row: typed.BaseCollectionAttributeCollectionNode) -> CollectionNode[T]:
            node = CollectionNode(
                value=pickle.loads(row.value),
                aliases=frozenset(row_id_to_aliases[row.id]),
                sort_value=row.sort_value,
                children=frozenset(),
                parent=parent,
                slot_type=self.slot_type
            )

            children_ids = row_id_to_child_row_ids.get(row.id, [])

            if children_ids:
                node._post_set_children(frozenset(
                    recursively_create_children(node, row_id_to_row[child_id])
                    for child_id in children_ids
                ))

            for syn in (node.value, *node.aliases):
                normed_syn_to_node[self.slot_type.norm(syn)] = node

            return node

        top_nodes = frozenset(recursively_create_children(None, row) for row in top_rows)
            
        return Collection(
            attribute=self,
            top_nodes=top_nodes,
            normed_syn_to_node=MappingProxyType(normed_syn_to_node)
        )


    def set_collection(
        self,
        top_raw_nodes: RawCollectionNodesT[T], 
    ) -> 'Collection[T]':
        with self.locked:
            if not top_raw_nodes:
                return Collection(
                    attribute=self,
                    top_nodes=frozenset(),
                    normed_syn_to_node=MappingProxyType({})
                )
            
            normed_to_node: dict[T, CollectionNode[T]] = {}
            node_count: int = 0

            def recursively_create_children(parent: None | CollectionNode[T], raw_node: RawCollectionNode[T], depth: int) -> CollectionNode[T]:
                if depth > MAX_DEPTH:
                    raise feedbacks.temp("Max collection depth exceeded")

                nonlocal node_count
                node_count += 1

                if node_count > MAX_ELEMS:
                    raise feedbacks.temp("Max amount of collection elems surpassed!")
                
                if not numbers.is_int32(raw_node.sort_value):
                    raise feedbacks.temp("Sort value out of range")
                
                normed_value: T = self.slot_type.norm(raw_node.value)
                aliases: set[T] = set(map(self.slot_type.norm, raw_node.aliases))

                if normed_value in aliases:
                    aliases.remove(normed_value)
                
                node = CollectionNode(
                    value=raw_node.value,
                    aliases=frozenset(aliases),
                    sort_value=raw_node.sort_value,
                    children=frozenset(),
                    parent=parent,
                    slot_type=self.slot_type
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

            TblNodes = self.__class__.tables.attribute_collection_node
            TblAliases = self.__class__.tables.attribute_collection_node_alias
            
            def recursively_insert_children(parent_id: int | None, nodes: CollectionNodesT[T]) -> None:
                if not nodes:
                    return
                
                for node in nodes:
                    c.execute(lambda arg: f"""
                        INSERT INTO {TblNodes} (
                            {TblNodes.attribute_id},
                            {TblNodes.value},
                            {TblNodes.sort_value},
                            {TblNodes.parent_id}
                        ) 
                        VALUES (
                            {arg(self.id)},
                            {arg(pickle.dumps(node.value))},
                            {arg(node.sort_value)},
                            {arg(parent_id)}
                        )
                    """)

                    node_id = c.last_generated_id

                    if node.aliases:
                        c.execute(lambda arg: f"""
                            INSERT INTO {TblAliases} (
                                {TblAliases.attribute_id},
                                {TblAliases.attribute_collection_node_id},
                                {TblAliases.alias}
                            )
                            VALUES 
                                {','.join(f"""(
                                    {arg(self.id)},
                                    {arg(node_id)},
                                    {arg(pickle.dumps(alias))}
                                )""" for alias in node.aliases)}
                        """)

                    recursively_insert_children(node_id, node.children)

            with queries.connected() as c, self.locked:
                # We go from top nodes down the tree so we can be sure
                # the parent_id is already inserted and the foreign key
                # check succeeds
                recursively_insert_children(None, top_nodes)

            return Collection(
                attribute=self,
                top_nodes=top_nodes,
                normed_syn_to_node=MappingProxyType(normed_to_node)
            )