import builtins
from collections import defaultdict
from dataclasses import dataclass
import itertools
from typing import TYPE_CHECKING, ClassVar, Final, Sequence, get_args

from database import queries, typed
from errors.feedback import feedbacks
from structures.attribute import slot_type
from structures.attribute import collection
from structures.attribute.slot_type import TypeStr, SlotType
from structures.attribute.collection import Collection, CollectionEntry
from structures import BaseStructure
from utils import text

if TYPE_CHECKING:
    from structures.list import List
    from structures.attribute.static_attribute import StaticAttribute
    from structures.attribute.task_attribute import TaskAttribute
    from structures.attribute.user_attribute import UserAttribute



type AnyAttributeT = StaticAttribute | TaskAttribute | UserAttribute

_any_attribute: tuple[type[StaticAttribute], type[TaskAttribute], type[UserAttribute]] | None = None

def ANY_ATTRIBUTE() -> tuple[type[StaticAttribute], type[TaskAttribute], type[UserAttribute]]:
    global _any_attribute
    
    if _any_attribute is not None:
        return _any_attribute

    return (_any_attribute := get_args(AnyAttributeT.__value__)) 

# General
SORT_KEY_NONE_NUMBER: Final[int] = max(abs(slot_type.NUMBER_MIN), abs(slot_type.NUMBER_MAX)) + 1

@dataclass(frozen=True, slots=True)
class AttributeTables:
    attribute: type[typed.BaseAttribute]
    attribute_alias: type[typed.BaseAttributeAlias]

@dataclass(frozen=True, slots=True)
class BaseNonStaticAttributeTables(AttributeTables):
    attribute_collection_entry: type[typed.BaseAttributeCollectionEntry]
    attribute_collection_entry_alias: type[typed.BaseAttributeCollectionEntryAlias]
    attribute_task_value: type[typed.BaseAttributeTaskValue]


class BaseAttribute(BaseStructure):
    tables: ClassVar[AttributeTables]
    
    list: 'List'
    id: int 
    real_name: text.RealStr
    norm_name: text.NormStr
    slot_type: SlotType
    position: int
    min_slots: int
    max_slots: int

    @property
    def identity(self) -> tuple[int, ...]:
        return (ANY_ATTRIBUTE().index(self.__class__), self.id) + self.list.identity
    
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
    
    def get_collection(self) -> Collection:
        return Collection(attribute=self, entries=())

    def raw_to_slots(self, value: Sequence[str]) -> builtins.list[TypeStr]:
        if not (self.min_slots <= (count := len(value)) <= self.max_slots):
            raise feedbacks.temp("Count of values not between limits", min=self.min_slots, count=count, max=self.max_slots)
        
        return [self.slot_type.raw_to_slot(slot) for slot in value]
        


class BaseNonStaticAttribute(BaseAttribute):
    tables: ClassVar[BaseNonStaticAttributeTables]

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.__class__ == BaseNonStaticAttribute:
            raise RuntimeError
    

    def raw_to_slots(self, value: Sequence[str]) -> builtins.list[TypeStr]:
        converted = super().raw_to_slots(value)
        collection = self.get_collection()

        if not collection:
            return converted
        
        result: list[TypeStr] = []

        for slot in value:
            node = collection.get_entry_by_syn(slot)

            if node is None:
                raise feedbacks.temp("Collection node not found")
            
            result.append(node.value)

        return result


    def get_collection(self) -> Collection:
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
                    {TblAlias.type_alias}
                FROM
                    {TblAlias}
                WHERE
                    {TblAlias.attribute_id} = {arg(self.id)}
                ORDER
            """)

            alias_rows = c.fetchall(TblAlias)

        entry_id_to_aliases: defaultdict[int, set[slot_type.TypeStr]] = defaultdict(set)
        
        for alias_row in alias_rows:
            alias = self.slot_type.raw_to_slot(alias_row.type_alias)
            entry_id_to_aliases[alias_row.attribute_collection_entry_id].add(alias)
        
        entries: tuple[CollectionEntry, ...] = tuple(
            CollectionEntry(
                id=entry_row.id,
                value=entry_row.type_slot,
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
        raw_collection: Sequence[str], 
    ) -> 'Collection':
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

            norm_syns: set[text.NormStr] = set()
            
            type_slots: list[TypeStr] = []
            norm_slots: list[text.NormStr] = []
            
            combined_real_aliases: tuple[set[text.RealStr], ...] = tuple(set() for _ in range(count))
            combined_norm_aliases: tuple[set[text.NormStr], ...] = tuple(set() for _ in range(count))

            for i, entry in enumerate(raw_collection):
                for j, syn_str in enumerate((entry['slot'], *entry['aliases'])):
                    real_syn = self.slot_type.raw_to_slot(syn_str)
                    norm_syn = self.slot_type.norm(real_syn)

                    if norm_syn in norm_syns:
                        raise feedbacks.temp(f"Slot or alias {norm_syn} seen twice in collection. Must be unique!")
                    
                    norm_syns.add(norm_syn)
                    
                    if j == 0:
                        type_slots.append(real_syn)
                        norm_slots.append(norm_syn)
                    else:
                        combined_real_aliases[i].add(real_syn)
                        combined_norm_aliases[i].add(norm_syn)

            c.executemany(lambda args: t"""
                INSERT INTO {TblEntry} (
                    {TblEntry.attribute_id},
                    {TblEntry.index},
                    {TblEntry.norm_slot},
                    {TblEntry.type_slot}
                )
                VALUES (
                    {args(itertools.repeat(self.id, count))},
                    {args(range(0, count))},
                    {args(norm_slots)},
                    {args(type_slots)}
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
                    {TblAlias.type_alias}
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
                    value=type_slots[i],
                    aliases=frozenset(combined_real_aliases[i])
                )
                for i in range(count)
            )

            return Collection(
                attribute=self,
                entries=entries
            )     