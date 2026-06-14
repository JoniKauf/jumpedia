from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeSlotType
from domain.value_objects.community import CommunityLimits
import typing as t

from domain.value_objects.string import StrStore

if t.TYPE_CHECKING:

    class AttributeName(StrStore):
        pass

else:
    AttributeName = factories.make_constrained_str_store_type(
        "AttributeName", CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX, AttributeEntity
    )


TMin = t.TypeVar("TMin", bound=int, covariant=True, default=int)


@dataclass(frozen=True, unsafe_hash=True, slots=True)
class AttributeSlot(t.Generic[TMin]):
    type: AttributeSlotType
    min_count: TMin
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
