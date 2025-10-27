import builtins
import itertools
import typing as t
from collections import defaultdict
from dataclasses import dataclass, field

from src.utils import orm, text

from .. import BaseStructure
from ..jumpedia import db
from .collection import Collection, CollectionEntry
from .slot_type import SlotStr, SlotType

if t.TYPE_CHECKING:
    from ..list import KindT, List
    
# General
SORT_KEY_NONE_NUMBER: t.Final[int] = max(abs(slot_type.NUMBER_MIN), abs(slot_type.NUMBER_MAX)) + 1

@dataclass(frozen=True, slots=True)
class AttributeTables:
    attribute: type[db.AnyAttributeTable]
    attribute_alias: type[db.AnyAttributeAliasTable]

@dataclass(frozen=True, slots=True)
class BaseNonStaticAttributeTables(AttributeTables):
    attribute_collection_entry: type[db.AnyAttributeCollectionEntryTable]
    attribute_collection_entry_alias: type[db.AnyAttributeCollectionEntryAliasTable]
    attribute_task_value: type[db.AnyAttributeTaskValueTable]

type AttributeTypeId = t.Literal[0, 1, 2]

class BaseAttribute(BaseStructure):
    tables: t.ClassVar[AttributeTables]
    type_id: t.ClassVar[AttributeTypeId]
    
    list: 'List'
    id: int 
    real_name: text.RealStr
    norm_name: text.NormStr
    slot_type: SlotType
    position: int
    min_slots: int
    max_slots: int
    kind: KindT | None = None

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.__class__.type_id, self.id) + self.list.identity
    
    @property
    def name(self) -> str:
        return self.real_name
    
    @property
    def required(self) -> bool:
        return self.min_slots > 0
    
    @property
    def connector(self) -> orm.Connector:
        return self.list.connector
    
    # --- Methods ---

    def __post_init__(self) -> None:
        if self.__class__ == BaseAttribute:
            raise RuntimeError()

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    def _get_aliases_rows[T: db.AnyAttributeAliasTable](self, table: type[T], column: orm.Column[T, t.Any]) -> list[T]:
        with self.connector.cursor() as c:
            return c.select(
                column,
                from_=table
            ).where(
                (table.list_id, orm.Operator.EQ, self.list.id),
                (table.attribute_id, orm.Operator.EQ, self.id)
            ).fetch_all()
        
    def get_real_aliases(self) -> frozenset[text.RealStr]:
        AttributeAliasTable = self.__class__.tables.attribute_alias
        return frozenset(row.real_alias for row in self._get_aliases_rows(AttributeAliasTable, AttributeAliasTable.real_alias))  # type: ignore
    
    def get_norm_aliases(self) -> frozenset[text.NormStr]:
        AttributeAliasTable = self.__class__.tables.attribute_alias
        return frozenset(row.norm_alias for row in self._get_aliases_rows(AttributeAliasTable, AttributeAliasTable.norm_alias))  # type: ignore
    
    def get_collection(self) -> Collection:
        return Collection(attribute=self, entries=())

    def raw_to_value(self, value: t.Sequence[str]) -> builtins.list[SlotStr]:
        if not (self.min_slots <= (count := len(value)) <= self.max_slots):
            raise feedbacks.temp("Count of values not between limits", min=self.min_slots, count=count, max=self.max_slots)
        
        return [self.slot_type.raw_to_slot(slot) for slot in value]


class RawCollectionEntryItem(t.NamedTuple):
    value: str
    aliases: t.Iterable[str]


class BaseNonStaticAttribute(BaseAttribute):
    tables: t.ClassVar[BaseNonStaticAttributeTables]

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.__class__ == BaseNonStaticAttribute:
            raise RuntimeError
    

    def raw_to_value(self, value: t.Sequence[str]) -> builtins.list[SlotStr]:
        converted = super().raw_to_value(value)
        collection = self.get_collection()

        if not collection:
            return converted
        
        result: list[SlotStr] = []

        for slot in value:
            node = collection.get_entry_by_syn(slot)

            if node is None:
                raise feedbacks.temp("Collection node not found")
            
            result.append(node.value)

        return result


    def get_collection(self) -> Collection:
        AttributeCollectionEntryTable = self.__class__.tables.attribute_collection_entry
        AttributeCollectionEntryAliasTable = self.__class__.tables.attribute_collection_entry_alias

        with self.connector.cursor() as c:
            entry_rows = c.select(
                '*',
                from_=AttributeCollectionEntryTable
            ).where(
                (AttributeCollectionEntryTable.attribute_id, orm.Operator.EQ, self.id)
            ).fetch_all()

            if not entry_rows:
                return Collection(attribute=self, entries=())
            
            alias_rows = c.select(
                AttributeCollectionEntryAliasTable.attribute_collection_entry_id,  # type: ignore
                AttributeCollectionEntryAliasTable.slot_alias,  # type: ignore
                from_=AttributeCollectionEntryAliasTable
            ).where(
                (AttributeCollectionEntryAliasTable.attribute_id, orm.Operator.EQ, self.id)
            ).fetch_all()

        entry_id_to_aliases: defaultdict[int, set[slot_type.SlotStr]] = defaultdict(set)
        
        for alias_row in alias_rows:
            alias = self.slot_type.raw_to_slot(alias_row.slot_alias)
            entry_id_to_aliases[alias_row.attribute_collection_entry_id].add(alias)
        
        entries: tuple[CollectionEntry, ...] = tuple(
            CollectionEntry(
                id=entry_row.id,
                value=entry_row.slot_slot,
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
        collection: t.Sequence[text.RealStr], 
    ) -> 'Collection':
        count = len(collection)

        if not count:
            return Collection(attribute=self, entries=())

        if count > self.list.community.jumpedia.limits:
            raise feedbacks.temp(f"Limit fo {collection.MAX_ENTRIES} surpassed!")
        
        AttributeCollectionEntryTable = self.__class__.tables.attribute_collection_entry
        AttributeCollectionEntryAliasTable = self.__class__.tables.attribute_collection_entry_alias
        
        with self.locked, self.connector.cursor() as c:
            c.delete(
                from_=AttributeCollectionEntryTable
            ).where(
                (AttributeCollectionEntryTable.attribute_id, orm.Operator.EQ, self.id)
            ).execute()

            norm_syns: set[text.NormStr] = set()
            
            type_slots: list[SlotStr] = []
            norm_slots: list[text.NormStr] = []
            
            combined_real_aliases: tuple[set[SlotStr], ...] = tuple(set() for _ in range(count))
            combined_norm_aliases: tuple[set[text.NormStr], ...] = tuple(set() for _ in range(count))

            for i, entry in enumerate(collection):
                for j, syn_str in enumerate((entry.value, *entry.aliases)):
                    type_syn = self.slot_type.raw_to_slot(syn_str)
                    norm_syn = text.real_to_norm(type_syn)

                    if norm_syn in norm_syns:
                        raise feedbacks.temp(f"Slot or alias {norm_syn} seen twice in collection. Must be unique!")
                    
                    norm_syns.add(norm_syn)
                    
                    if j == 0:
                        type_slots.append(type_syn)
                        norm_slots.append(norm_syn)
                    else:
                        combined_real_aliases[i].add(type_syn)
                        combined_norm_aliases[i].add(norm_syn)

            c.executemany(lambda args: t"""
                INSERT INTO {AttributeCollectionEntryTable} (
                    {AttributeCollectionEntryTable.attribute_id},
                    {AttributeCollectionEntryTable.index},
                    {AttributeCollectionEntryTable.norm_slot},
                    {AttributeCollectionEntryTable.slot_slot}
                )
                VALUES (
                    {args(itertools.repeat(self.id, count))},
                    {args(range(0, count))},
                    {args(norm_slots)},
                    {args(type_slots)}
                )
                RETURNING {AttributeCollectionEntryTable.index}, {AttributeCollectionEntryTable.id}
            """)

            idx_to_id: list[int] = [0 for _ in range(count)]
            
            for row in c.fetchall(AttributeCollectionEntryTable):
                idx_to_id[row.index] = row.id

            combined_aliases_count = 0
            entry_ids: list[int] = []

            for i, aliases in enumerate(combined_norm_aliases):
                entry_id = idx_to_id[i]
                aliases_count = len(aliases)

                combined_aliases_count += aliases_count
                entry_ids.extend(itertools.repeat(entry_id, aliases_count))

            c.executemany(lambda args: t"""
                INSERT INTO {AttributeCollectionEntryAliasTable} (
                    {AttributeCollectionEntryAliasTable.attribute_id},
                    {AttributeCollectionEntryAliasTable.attribute_collection_entry_id},
                    {AttributeCollectionEntryAliasTable.norm_alias},
                    {AttributeCollectionEntryAliasTable.slot_alias}
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
        

class StaticAttribute(BaseAttribute):
    tables = AttributeTables(db.StaticAttribute, db.StaticAttributeAlias)
    type_id = 0
    
    kind: KindT = field(default=None)  # pyright: ignore[reportAssignmentType]

    def __post_init__(self) -> None:
        from structures.list import KINDS

        if self.kind not in KINDS:
            raise TypeError(f"kind {self.kind} not in {KINDS}")

        return super().__post_init__()
    

class TaskAttribute(BaseNonStaticAttribute):
    tables = BaseNonStaticAttributeTables(
        db.TaskAttribute,
        db.TaskAttributeAlias,
        db.TaskAttributeCollectionEntry,
        db.TaskAttributeCollectionEntryAlias,
        db.TaskAttributeTaskValue,
    )
    type_id = 1


class UserAttribute(BaseNonStaticAttribute):
    tables = BaseNonStaticAttributeTables(
        db.UserAttribute,
        db.UserAttributeAlias,
        db.UserAttributeCollectionEntry,
        db.UserAttributeCollectionEntryAlias,
        db.UserAttributeTaskValue,
    )
    type_id = 2


type AnyAttributeT = StaticAttribute | TaskAttribute | UserAttribute

ALL_ATTRIBUTE_TYPES = (StaticAttribute, TaskAttribute, UserAttribute)


@t.overload
def type_id_to_type(type_id: t.Literal[0]) -> type[StaticAttribute]:
    pass

@t.overload
def type_id_to_type(type_id: t.Literal[1]) -> type[TaskAttribute]:
    pass

@t.overload
def type_id_to_type(type_id: t.Literal[2]) -> type[UserAttribute]:
    pass

def type_id_to_type(type_id: AttributeTypeId) -> type[AnyAttributeT]:
    return ALL_ATTRIBUTE_TYPES[type_id]