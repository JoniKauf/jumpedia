import itertools
import typing as t
from collections import defaultdict
from dataclasses import dataclass, field

from src.utils import orm, text

from .. import errors

from .. import BaseStructure
from ..jumpedia import db
from .collection import Collection, CollectionEntry
from .slot_str import SlotStr, SlotTypeT

if t.TYPE_CHECKING:
    from ..list import KindT, List

# General
SORT_KEY_NONE_NUMBER: t.Final[int] = (
    max(abs(slot_str.NUMBER_MIN), abs(slot_str.NUMBER_MAX)) + 1
)


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

    list: "List"
    id: int
    real_name: text.RealStr
    norm_name: text.NormStr
    slot_type: type[SlotTypeT]
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

    def _get_aliases_rows(
        self,
        table: type[db.AbstractAttributeAliasTable],
        column: orm.Column[db.AbstractAttributeAliasTable, t.Any],
    ) -> list[db.AbstractAttributeAliasTable]:
        with self.connector.cursor() as c:
            return c.fetch_all(
                table.select(column).where(
                    (table.list_id, orm.Operator.EQ, self.list.id),
                    (table.attribute_id, orm.Operator.EQ, self.id),
                )
            )

    def get_real_aliases(self) -> frozenset[text.RealStr]:
        AttributeAliasTable = self.__class__.tables.attribute_alias
        return frozenset(row.real_alias for row in self._get_aliases_rows(AttributeAliasTable, AttributeAliasTable.real_alias))  # type: ignore

    def get_norm_aliases(self) -> frozenset[text.NormStr]:
        AttributeAliasTable = self.__class__.tables.attribute_alias
        return frozenset(row.norm_alias for row in self._get_aliases_rows(AttributeAliasTable, AttributeAliasTable.norm_alias))  # type: ignore

    def get_collection(self) -> Collection:
        return Collection(attribute=self, entries=())

    def real_to_slot(self, value: t.Sequence[text.RealStr]) -> tuple[SlotStr, ...]:
        if not (self.min_slots <= len(value) <= self.max_slots):
            raise errors.AttributeValueSlotCountOutOfValidRange(
                value,
                self
            )

        return tuple(SlotStr(slot, self.slot_type) for slot in value)


class RawCollectionEntryItem(t.NamedTuple):
    value: str
    aliases: t.Iterable[str]


class BaseNonStaticAttribute(BaseAttribute):
    tables: t.ClassVar[BaseNonStaticAttributeTables]

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.__class__ == BaseNonStaticAttribute:
            raise RuntimeError

    def real_to_slot(self, value: t.Sequence[text.RealStr]) -> tuple[SlotStr, ...]:
        converted = super().real_to_slot(value)
        collection = self.get_collection()

        if not collection:
            return converted

        result: list[SlotStr] = []

        for slot in value:
            real_slot = text.RealStr(slot)
            node = collection.get_entry_by_syn(text.NormStr(real_slot))

            if node is None:
                raise errors.CollectionEntryNotFound(
                    real_slot,
                    collection
                )

            result.append(node.value)

        return tuple(result)

    def get_collection(self) -> Collection:
        AttributeCollectionEntryTable = t.cast(
            type[db.AbstractAttributeCollectionEntryTable],
            self.__class__.tables.attribute_collection_entry,
        )
        AttributeCollectionEntryAliasTable = t.cast(
            type[db.AbstractAttributeCollectionEntryAliasTable],
            self.__class__.tables.attribute_collection_entry_alias,
        )

        with self.connector.cursor() as c:
            entry_rows = c.fetch_all(
                AttributeCollectionEntryTable.select("*").where(
                    (
                        AttributeCollectionEntryTable.attribute_id,
                        orm.Operator.EQ,
                        self.id,
                    )
                )
            )

            if not entry_rows:
                return Collection(attribute=self, entries=())

            alias_rows = c.fetch_all(
                AttributeCollectionEntryAliasTable.select(
                    AttributeCollectionEntryAliasTable.attribute_collection_entry_id,
                    AttributeCollectionEntryAliasTable.slot_alias,
                ).where(
                    (
                        AttributeCollectionEntryAliasTable.attribute_id,
                        orm.Operator.EQ,
                        self.id,
                    )
                )
            )

        entry_id_to_aliases: defaultdict[int, set[slot_str.SlotStr]] = defaultdict(set)

        for alias_row in alias_rows:
            alias = SlotStr(alias_row.slot_alias, self.slot_type)
            entry_id_to_aliases[alias_row.attribute_collection_entry_id].add(alias)

        entries: tuple[CollectionEntry, ...] = tuple(
            CollectionEntry(
                id=entry_row.id,
                value=entry_row.slot_slot,
                collection_index=entry_row.index,
                aliases=frozenset(entry_id_to_aliases[entry_row.id]),
            )
            for entry_row in entry_rows
        )

        return Collection(attribute=self, entries=entries)

    def set_collection(
        self,
        collection: t.Sequence[tuple[text.RealStr, t.Iterable[text.RealStr]]],
    ) -> "Collection":
        count = len(collection)

        if not count:
            return Collection(attribute=self, entries=())

        if count > self.list.community.limits.attribute_collection_entry_count_max:
            raise errors.LimitReachedError(
                self.list.community.limits.attribute_collection_entry_count_max,
                Collection
            )

        AttributeCollectionEntryTable = t.cast(
            type[db.AbstractAttributeCollectionEntryTable],
            self.__class__.tables.attribute_collection_entry,
        )
        AttributeCollectionEntryAliasTable = t.cast(
            type[db.AbstractAttributeCollectionEntryAliasTable],
            self.__class__.tables.attribute_collection_entry_alias,
        )

        norm_syns: set[text.NormStr] = set()

        type_slots: list[SlotStr] = []
        norm_slots: list[text.NormStr] = []

        combined_real_aliases: tuple[set[SlotStr], ...] = tuple(
            set() for _ in range(count)
        )
        combined_norm_aliases: tuple[set[text.NormStr], ...] = tuple(
            set() for _ in range(count)
        )

        for i, (value, aliases) in enumerate(collection):
            for j, syn_str in enumerate((value, *aliases)):
                slot_syn = SlotStr(syn_str, self.slot_type)
                norm_syn = text.NormStr(slot_syn)

                if norm_syn in norm_syns:
                    raise errors.CollectionEntryDuplicate(slot_syn)

                norm_syns.add(norm_syn)

                if j == 0:
                    type_slots.append(slot_syn)
                    norm_slots.append(norm_syn)
                else:
                    combined_real_aliases[i].add(slot_syn)
                    combined_norm_aliases[i].add(norm_syn)


        with self.locked, self.connector.cursor() as c:
            c.execute(
                AttributeCollectionEntryTable.delete().where(
                    (
                        AttributeCollectionEntryTable.attribute_id,
                        orm.Operator.EQ,
                        self.id,
                    )
                )
            )

            rows = c.fetch_all(
                AttributeCollectionEntryTable.insert(
                    AttributeCollectionEntryTable.attribute_id.bind(
                        *itertools.repeat(self.id, count)
                    ),
                    AttributeCollectionEntryTable.index.bind(*range(0, count)),
                    AttributeCollectionEntryTable.norm_slot.bind(*norm_slots),
                    AttributeCollectionEntryTable.slot_slot.bind(*type_slots),
                ).returning(
                    AttributeCollectionEntryTable.index,
                    AttributeCollectionEntryTable.id,
                )
            )

            idx_to_id: list[int] = [0 for _ in range(count)]

            for row in rows:
                idx_to_id[row.index] = row.id

            combined_aliases_count = 0
            entry_ids: list[int] = []

            for i, aliases in enumerate(combined_norm_aliases):
                entry_id = idx_to_id[i]
                aliases_count = len(aliases)

                combined_aliases_count += aliases_count
                entry_ids.extend(itertools.repeat(entry_id, aliases_count))

            c.execute(
                AttributeCollectionEntryAliasTable.insert(
                    AttributeCollectionEntryAliasTable.attribute_id.bind(
                        *itertools.repeat(self.id, combined_aliases_count)
                    ),
                    AttributeCollectionEntryAliasTable.attribute_collection_entry_id.bind(
                        *entry_ids
                    ),
                    AttributeCollectionEntryAliasTable.norm_alias.bind(
                        *itertools.chain(*combined_norm_aliases)
                    ),
                    AttributeCollectionEntryAliasTable.slot_alias.bind(
                        *itertools.chain(*combined_real_aliases)
                    ),
                )
            )

            entries: tuple[CollectionEntry, ...] = tuple(
                CollectionEntry(
                    id=idx_to_id[i],
                    collection_index=i,
                    value=type_slots[i],
                    aliases=frozenset(combined_real_aliases[i]),
                )
                for i in range(count)
            )

            return Collection(attribute=self, entries=entries)


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
