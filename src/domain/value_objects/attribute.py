import annotationlib
import itertools
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.errors import business
from domain.typing.attribute import (
    AnyAttributeTypeT,
    TaskAttributeTypeT,
    UserAttributeTypeT,
)
from domain.value_objects import factories
from domain.value_objects.community import CommunityLimits
from domain.value_objects.position import Position
from domain.value_objects.string import Str

if t.TYPE_CHECKING:

    class AttributeSynStr(Str):
        pass

else:
    AttributeSynStr = factories.make_length_limited_str_store_type(
        "AttributeSynStr", CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX, AttributeEntity
    )


@dataclass(frozen=True, unsafe_hash=True, slots=True)
class AttributeFieldConfig:
    slot_type: AttributeSlotType
    min_slot_count: int
    max_slot_count: int
    unique_slots: bool

    def __post_init__(self) -> None:
        if not (
            CommunityLimits.FIELD_MIN_MIN_SLOT_COUNT
            <= self.min_slot_count
            <= self.max_slot_count
            and self.max_slot_count >= CommunityLimits.FIELD_MIN_MAX_SLOT_COUNT
        ):
            raise business.SlotCountDefinitionLimitExceeded(
                self.min_slot_count,
                self.max_slot_count,
                CommunityLimits.FIELD_MIN_MIN_SLOT_COUNT,
                CommunityLimits.FIELD_MIN_MAX_SLOT_COUNT,
                None,
            )


@dataclass(frozen=True, slots=True)
class KindedAttributeDefaultProperties:
    name: AttributeSynStr
    kind: AttributeKind
    field_config: AttributeFieldConfig
    position: Position

    DEFAULTS: t.ClassVar[t.Final[tuple[KindedAttributeDefaultProperties, ...]]]  # type: ignore


KindedAttributeDefaultProperties.DEFAULTS = (  # type: ignore
    KindedAttributeDefaultProperties(
        AttributeSynStr("ID"),
        AttributeKind.ID,
        AttributeFieldConfig(
            AttributeSlotType.INTEGER,
            1,
            1,
            False,
        ),
        Position(1),
    ),
    KindedAttributeDefaultProperties(
        AttributeSynStr("Name"),
        AttributeKind.NAME,
        AttributeFieldConfig(
            AttributeSlotType.STRING,
            1,
            1,
            False,
        ),
        Position(2),
    ),
    KindedAttributeDefaultProperties(
        AttributeSynStr("Alias"),
        AttributeKind.ALIAS,
        AttributeFieldConfig(
            AttributeSlotType.STRING,
            0,
            15,
            True,
        ),
        Position(3),
    ),
    KindedAttributeDefaultProperties(
        AttributeSynStr("Given At"),
        AttributeKind.GIVEN_AT,
        AttributeFieldConfig(
            AttributeSlotType.STRING,
            1,
            1,
            False,
        ),
        Position(4),
    ),
    KindedAttributeDefaultProperties(
        AttributeSynStr("Given By"),
        AttributeKind.GIVEN_BY,
        AttributeFieldConfig(
            AttributeSlotType.STRING,
            1,
            1,
            False,
        ),
        Position(5),
    ),
)
