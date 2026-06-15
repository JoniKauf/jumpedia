import itertools
import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeSlotType
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore

if t.TYPE_CHECKING:

    class AttributeSyn(StrStore):
        pass

else:
    AttributeSyn = factories.make_constrained_str_store_type(
        "AttributeSyn", CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX, AttributeEntity
    )


if t.TYPE_CHECKING:

    class AttributeCollectionEntrySyn(StrStore):
        pass

else:
    AttributeCollectionEntrySyn = factories.make_constrained_str_store_type(
        "CollectionEntrySyn", CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX, AttributeEntity
    )


@dataclass(frozen=True, unsafe_hash=True, slots=True)
class AttributeSlot:
    type: AttributeSlotType
    min_count: int
    max_count: int

    def __post_init__(self) -> None:
        if not (
            CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MIN_SLOT_COUNT
            <= self.min_count
            <= self.max_count
            and self.max_count
            >= CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT
        ):
            raise errors.SlotCountLimitExceeded(
                self.min_count,
                self.max_count,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MIN_SLOT_COUNT,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT,
                None,
            )

@dataclass(frozen=True, unsafe_hash=True, slots=True)
class AttributeCollectionEntry:
    value: AttributeCollectionEntrySyn
    aliases: tuple[AttributeCollectionEntrySyn, ...]

@dataclass(frozen=True, unsafe_hash=True, slots=True)
class AttributeCollection:
    entries: tuple[AttributeCollectionEntry, ...]

    def __post_init__(self) -> None:
        all_syns = tuple(syn for entry in self.entries for syn in (entry.value, *entry.aliases))
        StrStore.unique(all_syns)