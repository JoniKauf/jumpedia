from dataclasses import dataclass
import typing as t


@dataclass(frozen=True, unsafe_hash=True)
class Limits:
    community_list_count_max: int
    list_attribute_count_max: int
    list_task_count_max: int
    attribute_alias_count_max: int
    attribute_task_value_slot_count_max: int
    attribute_collection_entry_count_max: int
    attribute_collection_entry_alias_count_max: int

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
    
    COMMUNITY_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = 64  # Db needs a maximum varchar
    LIST_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = 64  # Db needs a maximum varchar
    USER_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = 32 # Discord limit
    ATTRIBUTE_SYN_LENGTH_MAX: t.ClassVar[t.Final[int]] = 64  # Db needs a maximum varchar
    ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX: t.ClassVar[t.Final[int]] = 255  # Db needs a maximum varchar