import typing as t
from dataclasses import Field, dataclass

from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.errors.business import CommunityLimitOutOfRange
from jumpedia.domain.value_objects import factories

lazy from jumpedia.domain.value_objects.string import Str
from jumpedia.infrastructure.types.classproperty import cached_classproperty


@dataclass(frozen=True, unsafe_hash=True, kw_only=True, slots=True)
class CommunityLimits:
    community_list_count_max: int
    list_attribute_count_max: int
    list_task_count_max: int
    attribute_alias_count_max: int
    field_slot_count_max: int
    collection_entry_count_max: int
    collection_entry_alias_count_max: int

    def __post_init__(self) -> None:
        GENERAL_MIN: t.Final[int] = 0
        GENERAL_MAX: t.Final[int] = 255

        for name, field in self.__dataclass_fields__.items():
            field: Field

            limit: int = getattr(self, field.name)

            match name:
                case "field_slot_count_max":
                    if (
                        limit < CommunityLimits.FIELD_MIN_MAX_SLOT_COUNT
                        or limit > GENERAL_MAX
                    ):
                        raise CommunityLimitOutOfRange(
                            Str(name),
                            limit,
                            CommunityLimits.FIELD_MIN_MAX_SLOT_COUNT,
                            GENERAL_MAX,
                        )
                case "list_task_count_max":
                    TASK_MAX: int = 2**31 - 1

                    if limit < GENERAL_MIN or limit > TASK_MAX:
                        raise CommunityLimitOutOfRange(
                            Str(name), limit, GENERAL_MIN, TASK_MAX
                        )

                case "list_attribute_count_max":
                    if limit < GENERAL_MIN or limit > 127:
                        # Attribute count MUST be lower than half of max of
                        # TINYINT (255) because twice the space is needed for
                        # editing their position (temporarily all are offset)
                        raise CommunityLimitOutOfRange(
                            Str(name), limit, GENERAL_MIN, 127
                        )

                case _:
                    if limit < GENERAL_MIN or limit > GENERAL_MAX:
                        raise CommunityLimitOutOfRange(
                            Str(name), limit, GENERAL_MIN, GENERAL_MAX
                        )

    @cached_classproperty
    def DEFAULT(cls) -> t.Self:
        cls = t.cast(type[t.Self], cls)

        return cls(
            community_list_count_max=1,
            list_attribute_count_max=16,
            list_task_count_max=100,
            attribute_alias_count_max=8,
            field_slot_count_max=32,
            collection_entry_count_max=32,
            collection_entry_alias_count_max=8,
        )

    COMMUNITY_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = (
        64  # Db needs a maximum varchar
    )
    LIST_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = 64  # Db needs a maximum varchar
    USER_NAME_LENGTH_MAX: t.ClassVar[t.Final[int]] = 32  # Discord limit
    ATTRIBUTE_SYN_LENGTH_MAX: t.ClassVar[t.Final[int]] = (
        64  # Db needs a maximum varchar
    )
    FIELD_SLOT_LENGTH_MAX: t.ClassVar[t.Final[int]] = 255  # Db needs a maximum varchar

    FIELD_MIN_MIN_SLOT_COUNT: t.ClassVar[t.Final[int]] = 0  # minimum number min may be
    FIELD_MIN_MAX_SLOT_COUNT: t.ClassVar[t.Final[int]] = (
        1  # minimum number max may be; max must also be bigger than min
    )


if t.TYPE_CHECKING:

    class CommunityNameStr(Str):
        pass

else:
    CommunityNameStr = factories.make_length_limited_str_store_type(
        "CommunityNameStr", CommunityLimits.COMMUNITY_NAME_LENGTH_MAX, Concept.COMMUNITY
    )
