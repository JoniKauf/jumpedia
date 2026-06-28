import itertools
import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeSlotType
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class AttributeSynStr(Str):
        pass

else:
    AttributeSynStr = factories.make_length_limited_str_store_type(
        "AttributeSynStr", CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX, AttributeEntity
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
            raise errors.SlotCountDefinitionLimitExceeded(
                self.min_count,
                self.max_count,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MIN_SLOT_COUNT,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT,
                None,
            )
