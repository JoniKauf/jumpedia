import typing as t
from dataclasses import dataclass

from typing_extensions import Self

from domain import errors
from domain.entities.community import CommunityEntity
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore

if t.TYPE_CHECKING:

    class CommunityName(StrStore):
        pass

else:
    CommunityName = factories.make_length_limited_str_store_type(
        "CommunityName", CommunityLimits.COMMUNITY_NAME_LENGTH_MAX, CommunityEntity
    )


@dataclass(frozen=True, unsafe_hash=True, kw_only=True, slots=True)
class CommunityLimits:
    community_list_count_max: int
    list_attribute_count_max: int
    list_task_count_max: int
    attribute_alias_count_max: int
    attribute_task_value_slot_count_max: int
    attribute_collection_entry_count_max: int
    attribute_collection_entry_alias_count_max: int

    def __post_init__(self) -> None:
        if not (
            CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT
            <= self.attribute_task_value_slot_count_max
        ):
            raise ValueError("Community limit of slot count max too high")

        for name, limit in self.__dataclass_fields__.items():
            limit: int

            if not (0 <= limit <= 2 * 32 - 1):
                raise ValueError(f"{name} out of bounds ({limit})")

    @classmethod
    def default(cls) -> t.Self:
        return cls(
            community_list_count_max=1,
            list_attribute_count_max=16,
            list_task_count_max=100,
            attribute_alias_count_max=8,
            attribute_task_value_slot_count_max=32,
            attribute_collection_entry_count_max=32,
            attribute_collection_entry_alias_count_max=8,
        )

    COMMUNITY_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = (
        64  # Db needs a maximum varchar
    )
    LIST_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = 64  # Db needs a maximum varchar
    USER_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = 32  # Discord limit
    ATTRIBUTE_SYN_LENGTH_MAX: t.ClassVar[t.Final[int]] = (
        64  # Db needs a maximum varchar
    )
    ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX: t.ClassVar[t.Final[int]] = (
        255  # Db needs a maximum varchar
    )

    ATTRIBUTE_TASK_VALUE_MIN_MIN_SLOT_COUNT: t.ClassVar[t.Final[int]] = (
        0  # minimum number min may be
    )
    ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT: t.ClassVar[t.Final[int]] = (
        1  # minimum number max may be; max must also be bigger than min
    )
