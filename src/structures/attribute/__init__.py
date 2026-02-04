import functools
import itertools
import typing as t
from collections import defaultdict

from utils import orm, text

from .. import BaseStructure, BaseStructureWithAliases, db, errors
from . import slot_str
from .collection import Collection, CollectionEntry
from .slot_str import SlotStr, SlotTypeT

if t.TYPE_CHECKING:
    from ..list import Kind, List


# General
SORT_KEY_NONE_NUMBER: t.Final[int] = (
    max(abs(slot_str.NUMBER_MIN), abs(slot_str.NUMBER_MAX)) + 1
)

type AttributeTypeId = t.Literal[0, 1, 2]
ALL_ATTRIBUTE_TYPE_IDS: t.Final[tuple[t.Literal[0], t.Literal[1], t.Literal[2]]] = (
    0,
    1,
    2,
)


class BaseAttribute(BaseStructureWithAliases, naming=("attribute", "attributes")):
    type_id: t.ClassVar[AttributeTypeId]

    list: List
    real_name: text.RealStr
    norm_name: text.NormStr
    slot_type: type[SlotTypeT]
    position: int
    min_slot_count: int
    max_slot_count: int
    kind: Kind | None

    @property
    def name(self) -> str:
        return self.real_name

    @property
    def required(self) -> bool:
        return self.min_slot_count > 0

    @property
    def unique_slots_across_list(self) -> bool:
        return False

    def get_aliases(self, c: orm.Cursor, /) -> frozenset[text.RealStr]:
        return self.get_real_aliases(c)

    # --- Methods ---

    def __post_init__(self) -> None:
        if self.__class__ == BaseAttribute:
            raise RuntimeError()

    def _get_aliases_rows(
        self,
        c: orm.Cursor,
        column: orm.Column[db.AttributeAlias, t.Any],
    ) -> list[db.AttributeAlias]:
        return c.fetch_all(
            db.AttributeAlias.select(column).where(
                (db.AttributeAlias.list_id, orm.Operator.EQ, self.list.id),
                (
                    db.AttributeAlias.attribute_type_id,
                    orm.Operator.EQ,
                    self.__class__.type_id,
                ),
                (db.AttributeAlias.attribute_id, orm.Operator.EQ, self.id),
            )
        )

    def get_real_aliases(self, c: orm.Cursor, /) -> frozenset[text.RealStr]:
        return frozenset(
            text.RealStr(row.real_alias, check=False)
            for row in self._get_aliases_rows(c, db.AttributeAlias.real_alias)
        )

    def get_norm_aliases(self, c: orm.Cursor, /) -> frozenset[text.NormStr]:
        return frozenset(
            text.NormStr(row.norm_alias, check=False)
            for row in self._get_aliases_rows(c, db.AttributeAlias.norm_alias)
        )

    @functools.lru_cache(16)
    def get_collection(self, c: orm.Cursor, /) -> Collection:
        return Collection(attribute=self, entries=())

    def real_to_slot_value(
        self, c: orm.Cursor, value: t.Sequence[text.RealStr], /
    ) -> tuple[SlotStr, ...]:
        if not (self.min_slot_count <= len(value) <= self.max_slot_count):
            raise errors.AttributeValueSlotCountOutOfRangeError(tuple(value), self)

        return tuple(
            SlotStr(slot, self.slot_type, self.list.community.jumpedia.limits)
            for slot in value
        )


class RawCollectionEntryItem(t.NamedTuple):
    value: str
    aliases: t.Iterable[str]


class BaseNonStaticAttribute(
    BaseAttribute, naming=("task or user attribute", "task or user attributes")
):
    kind: None = None

    @property
    def unique_slots_across_list(self) -> bool:
        return False

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.__class__ == BaseNonStaticAttribute:
            raise RuntimeError

    def real_to_slot_value(
        self, c: orm.Cursor, value: t.Sequence[text.RealStr]
    ) -> tuple[SlotStr, ...]:
        converted = super().real_to_slot_value(c, value)
        collection = self.get_collection(c)

        if not collection:
            return converted

        result: list[SlotStr] = []

        for slot in value:
            real_slot = text.RealStr(slot)
            node = collection.get_entry_by_syn(text.NormStr(real_slot), None)

            if node is None:
                raise errors.CollectionEntryNotFoundError(real_slot, collection)

            result.append(node.value)

        return tuple(result)

    @functools.lru_cache(16)
    def get_collection(self, c: orm.Cursor, /) -> Collection:
        AttributeCollectionEntryTable = db.AttributeCollectionEntry
        AttributeCollectionEntryAliasTable = db.AttributeCollectionEntryAlias

        entry_rows = c.fetch_all(
            AttributeCollectionEntryTable.select("*")
            .where(
                (
                    AttributeCollectionEntryTable.attribute_id,
                    orm.Operator.EQ,
                    self.id,
                )
            )
            .order_by(AttributeCollectionEntryTable.index)
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
            alias = SlotStr(
                alias_row.slot_alias,
                self.slot_type,
                self.list.community.jumpedia.limits,
            )
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
        c: orm.Cursor,
        collection: t.Sequence[tuple[text.RealStr, t.Sequence[text.RealStr]]],
    ) -> Collection:
        count = len(collection)

        if not count:
            return Collection(attribute=self, entries=())

        if count > self.list.community.limits["attribute_collection_entry_count_max"]:
            raise errors.CollectionEntryLimitReachedError(
                count,
                self.list.community.limits["attribute_collection_entry_count_max"],
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

        alias_limit = self.list.community.limits[
            "attribute_collection_entry_alias_count_max"
        ]

        for i, (value, aliases) in enumerate(collection):
            if len(aliases) > alias_limit:
                raise errors.CollectionEntryAliasLimitReachedError(
                    SlotStr(value, self.slot_type, self.list.community.jumpedia.limits),
                    len(aliases),
                    alias_limit,
                )
            for j, syn_str in enumerate((value, *aliases)):
                slot_syn = SlotStr(
                    syn_str, self.slot_type, self.list.community.jumpedia.limits
                )
                norm_syn = text.NormStr(slot_syn)

                if norm_syn in norm_syns:
                    raise errors.CollectionEntrySynNotUniqueError(slot_syn)

                norm_syns.add(norm_syn)

                if j == 0:
                    type_slots.append(slot_syn)
                    norm_slots.append(norm_syn)
                else:
                    combined_real_aliases[i].add(slot_syn)
                    combined_norm_aliases[i].add(norm_syn)

        AttributeCollectionEntryTable = db.AttributeCollectionEntry
        AttributeCollectionEntryAliasTable = db.AttributeCollectionEntryAlias

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

        if combined_aliases_count:
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


class StaticAttribute(BaseAttribute, naming=("static attribute", "static attributes")):
    type_id = 0

    kind: Kind

    @property
    def unique_slots_across_list(self) -> bool:
        return True


class TaskAttribute(
    BaseNonStaticAttribute, naming=("task attribute", "task attributes")
):
    type_id = 1


class UserAttribute(
    BaseNonStaticAttribute, naming=("user attribute", "user attributes")
):
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


@t.overload
def type_id_to_type(type_id: int) -> type[AnyAttributeT]:
    pass


def type_id_to_type(type_id: int) -> type[AnyAttributeT]:
    return ALL_ATTRIBUTE_TYPES[type_id]
