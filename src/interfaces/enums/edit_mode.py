import enum

from domain.enums.edit_mode import (
    AliasEditMode,
    CollectionEditMode,
    FieldMappingEditMode,
)

AliasEditModeInterfaceEnum = enum.Enum(
    "AliasEditModeInterfaceEnum",
    [
        ("Replace Current Aliases", AliasEditMode.REPLACE.value),
        (
            "Combine With Current Aliases - Override On Collision",
            AliasEditMode.COMBINE_OVERRIDE_ON_COLLISION.value,
        ),
        (
            "Combine With Current Aliases - Error On Collision",
            AliasEditMode.COMBINE_ERROR_ON_COLLISION.value,
        ),
    ],
)

CollectionEditModeInterfaceEnum = enum.Enum(
    "CollectionEditModeInterfaceEnum",
    [
        ("Replace Current Collection", CollectionEditMode.REPLACE.value),
        (
            "Combine With Current Collection - Error On Any Value Or Alias Collision",
            CollectionEditMode.COMBINE_ERROR_ON_ANY_SYN_COLLISION.value,
        ),
    ],
)

FieldMappingEditModeInterfaceEnum = enum.Enum(
    "FieldMappingEditModeInterfaceEnum",
    [
        ("Replace Current Field Mapping", FieldMappingEditMode.REPLACE.value),
        (
            "Combine With Current Field Mapping - Override Slots On Attribute Collision",
            FieldMappingEditMode.COMBINE_OVERRIDE_ON_COLLISION.value,
        ),
        (
            "Combine With Current Field Mapping - Error On Attribute Collision",
            FieldMappingEditMode.COMBINE_ERROR_ON_COLLISION.value,
        ),
    ],
)
