import builtins
from collections import defaultdict
from dataclasses import dataclass
import itertools
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, TypedDict

from database import queries, typed
from errors.feedback import feedbacks
from structures.attribute import slot_type
from structures.attribute import collection
from structures.attribute.slot_type import LiteralToStrPossibleT, SlotType, SlotTypeT
from structures.attribute.collection import Collection, CollectionEntry
from structures import BaseStructure
from structures.list import List
from utils import parsetools, text

if TYPE_CHECKING:
    from structures.attribute.static_attribute import StaticAttribute
    from structures.attribute.task_attribute import TaskAttribute
    from structures.attribute.user_attribute import UserAttribute



type AnyAttributeT[T: SlotTypeT] = StaticAttribute[T] | TaskAttribute[T] | UserAttribute[T]
ANY_ATTRIBUTE = (StaticAttribute, TaskAttribute, UserAttribute)


class RawCollectionEntry(TypedDict):
    slot: str
    aliases: list[str]

type RawCollectionT[T] = list[RawCollectionEntry]

    

# General
SORT_KEY_NONE_NUMBER: Final[int] = max(abs(slot_type.NUMBER_MIN), abs(slot_type.NUMBER_MAX)) + 1


# Any of TYPES_LITERAL_ALLOWED or a list of any of TYPES_LITERAL_ALLOWED
type AttributeValueParseTypesT = LiteralToStrPossibleT | list[LiteralToStrPossibleT]
ATTRIBUTE_VALUE_PARSE_TYPES = (bool, int, str, [bool, int, str])

# Checking ATTRIBUTE_VALUE_PARSE_TYPES is too much effort and hard to generalize
# Just make sure it stays consistent when changing one


@dataclass(frozen=True, slots=True)
class AttributeTables:
    attribute: type[typed.BaseAttribute]
    attribute_alias: type[typed.BaseAttributeAlias]

@dataclass(frozen=True, slots=True)
class BaseNonStaticAttributeTables(AttributeTables):
    attribute_collection_entry: type[typed.BaseAttributeCollectionEntry]
    attribute_collection_entry_alias: type[typed.BaseAttributeCollectionEntryAlias]
    attribute_task_value: type[typed.BaseAttributeTaskValue]


class BaseAttribute[T: SlotTypeT](BaseStructure):
    tables: ClassVar[AttributeTables]
    allow_min_slots_on_creation: ClassVar[bool] = False
    deletable: ClassVar[bool] = True

    list: 'List'
    id: int 
    real_name: text.RealStr
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
    
    def get_real_aliases(self) -> frozenset[text.RealStr]:
        TblAlias = self.__class__.tables.attribute_alias

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {TblAlias.real_alias}
                FROM {TblAlias}
                WHERE {TblAlias.attribute_id} = {arg(self.id)}
            """)

            rows = c.fetchall(TblAlias)
        
        return frozenset(row.real_alias for row in rows)
    
    def get_norm_aliases(self) -> frozenset[text.NormStr]:
        TblAlias = self.__class__.tables.attribute_alias

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {TblAlias.norm_alias}
                FROM {TblAlias}
                WHERE {TblAlias.attribute_id} = {arg(self.id)}
            """)

            rows = c.fetchall(TblAlias)
        
        return frozenset(row.norm_alias for row in rows)
    
    def get_collection(self) -> Collection[T]:
        return Collection(attribute=self, entries=())

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
            
            if collection:
                result: list[int] = []

                for slot in v:
                    node = collection.get_entry_by_syn(slot)

                    if node is None:
                        raise ValueError
                    
                    result.append(node.collection_index * sign)
                
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

        if not collection:
            return value
        
        result: list[T] = []

        for slot in value:
            node = collection.get_entry_by_syn(slot)

            if node is None:
                raise feedbacks.temp("Collection node not found")
            
            result.append(node.value)

        return result


    def get_collection(self) -> Collection[T]:
        TblEntry = self.__class__.tables.attribute_collection_entry
        TblAlias = self.__class__.tables.attribute_collection_entry_alias

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {TblEntry}
                WHERE {TblEntry.attribute_id} = {arg(self.id)}
            """)

            entry_rows = c.fetchall(TblEntry)

            if not entry_rows:
                return Collection(attribute=self, entries=())
            
            c.execute(lambda arg: t"""
                SELECT 
                    {TblAlias.attribute_collection_entry_id},
                    {TblAlias.real_alias}
                FROM
                    {TblAlias}
                WHERE
                    {TblAlias.attribute_id} = {arg(self.id)}
                ORDER
            """)

            alias_rows = c.fetchall(TblAlias)

        entry_id_to_aliases: defaultdict[int, set[T]] = defaultdict(set)
        
        for alias_row in alias_rows:
            alias = self.slot_type.from_clean_str(alias_row.real_alias)
            entry_id_to_aliases[alias_row.attribute_collection_entry_id].add(alias)
        
        entries: tuple[CollectionEntry[T], ...] = tuple(
            CollectionEntry(
                id=entry_row.id,
                value=self.slot_type.from_clean_str(entry_row.real_slot),
                collection_index=entry_row.index,
                aliases=frozenset(entry_id_to_aliases[entry_row.id])
            ) 
            for entry_row in entry_rows
        )

        return Collection(
            attribute=self,
            entries=entries
        )
    
    def set_collection(
        self,
        raw_collection: RawCollectionT[T], 
    ) -> 'Collection[T]':
        count = len(raw_collection)

        if not count:
            return Collection(attribute=self, entries=())

        if count > collection.MAX_ENTRIES:
            raise feedbacks.temp(f"Limit fo {collection.MAX_ENTRIES} surpassed!")
        
        TblEntry = self.__class__.tables.attribute_collection_entry
        TblAlias = self.__class__.tables.attribute_collection_entry_alias
        
        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {TblEntry}
                WHERE {TblEntry.attribute_id} = {arg(self.id)}
            """)

            norm_syns: set[T] = set()
            
            real_slots: list[T] = []
            norm_slots: list[T] = []
            
            combined_real_aliases: tuple[set[T], ...] = tuple(set() for _ in range(count))
            combined_norm_aliases: tuple[set[T], ...] = tuple(set() for _ in range(count))

            for i, entry in enumerate(raw_collection):
                for j, syn_str in enumerate((entry['slot'], *entry['aliases'])):
                    real_syn = self.slot_type.from_raw_str(syn_str)
                    norm_syn = self.slot_type.norm(real_syn)

                    if norm_syn in norm_syns:
                        raise feedbacks.temp(f"Slot or alias {norm_syn} seen twice in collection. Must be unique!")
                    
                    norm_syns.add(norm_syn)
                    
                    if j == 0:
                        real_slots.append(real_syn)
                        norm_slots.append(norm_syn)
                    else:
                        combined_real_aliases[i].add(real_syn)
                        combined_norm_aliases[i].add(norm_syn)

            c.executemany(lambda args: t"""
                INSERT INTO {TblEntry} (
                    {TblEntry.attribute_id},
                    {TblEntry.index},
                    {TblEntry.norm_slot},
                    {TblEntry.real_slot}
                )
                VALUES (
                    {args(itertools.repeat(self.id, count))},
                    {args(range(0, count))},
                    {args(norm_slots)},
                    {args(real_slots)}
                )
                RETURNING {TblEntry.index}, {TblEntry.id}
            """)

            idx_to_id: list[int] = [0 for _ in range(count)]
            
            for row in c.fetchall(TblEntry):
                idx_to_id[row.index] = row.id

            combined_aliases_count = 0
            entry_ids: list[int] = []

            for i, aliases in enumerate(combined_norm_aliases):
                entry_id = idx_to_id[i]
                aliases_count = len(aliases)

                combined_aliases_count += aliases_count
                entry_ids.extend(itertools.repeat(entry_id, aliases_count))

            c.executemany(lambda args: t"""
                INSERT INTO {TblAlias} (
                    {TblAlias.attribute_id},
                    {TblAlias.attribute_collection_entry_id},
                    {TblAlias.norm_alias},
                    {TblAlias.real_alias}
                )
                VALUES (
                    {args(itertools.repeat(self.id, combined_aliases_count))},
                    {args(entry_ids)},
                    {args(itertools.chain(*combined_norm_aliases))},
                    {args(itertools.chain(*combined_real_aliases))}
                )
            """)
            
            entries: tuple[CollectionEntry, ...] = tuple(
                CollectionEntry(
                    id=idx_to_id[i], 
                    collection_index=i,
                    value=real_slots[i],
                    aliases=frozenset(combined_real_aliases[i])
                )
                for i in range(count)
            )

            return Collection(
                attribute=self,
                entries=entries
            )     